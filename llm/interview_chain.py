import json
import logging
import os
import uuid

import requests
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings

from llm.prompts import evaluation_system_prompt, interview_system_prompt, interview_user_prompt, evaluation_user_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class InterviewChain:
    """
    Manages the interview session, including generating questions, evaluating responses, and logging the conversation.
    """

    def __init__(self, config: dict) -> None:
        """
        Initialize the InterviewChain with configuration data.

        Args:
            config (dict): Configuration parameters for interview, vectorstore, and LLM.
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.llm_url = os.environ["OLLAMA_URL"]
        self.db_url = os.environ["DB_SERVICE_URL"]
        self.candidate_info = {}
        self.history = ""
        self.max_questions = self.config["max_questions"]
        self.question_count = 0
        self.vectorstore = self.init_vectorstore()
        self.session_id = None

    def init_candidate_info(self) -> None:
        """Initialize an empty candidate info dictionary."""
        self.candidate_info = {"name": "", "role": "", "email": ""}

    def init_new_session(self) -> None:
        """
        Initialize a new interview session by resetting history and candidate info and assigning a new session ID.
        """
        self.logger.info("Initializing new interview session.")
        self.history = ""
        self.init_candidate_info()
        self.question_count = 0
        self.session_id = uuid.uuid4()

    def init_vectorstore(self) -> FAISS:
        """
        Initialize the vectorstore from documents in the provided directory.

        Returns:
            FAISS: A vectorstore built from the split document chunks.
        """
        embedding = HuggingFaceEmbeddings(model_name=self.config["embedding_model"])
        dir_loader = DirectoryLoader(self.config["rag_dir_path"], glob="**/*.txt", loader_cls=TextLoader)
        docs = dir_loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config["text_splitter"]["chunk_size"],
            chunk_overlap=self.config["text_splitter"]["chunk_overlap"],
        )
        docs = splitter.split_documents(docs)
        vectorstore = FAISS.from_documents(docs, embedding)
        return vectorstore

    def add_candidate_info(self, name: str, role: str, email: str) -> None:
        """
        Add candidate information to the session.

        Args:
            name (str): Candidate's name.
            role (str): Role candidate applied for.
            email (str): Candidate's email address.
        """
        self.candidate_info["name"] = name
        self.candidate_info["role"] = role
        self.candidate_info["email"] = email

    def create_question_prompt(self, context: str) -> str:
        """
        Create the prompt for generating the next interview question.

        Args:
            context (str): Additional context from the vectorstore.

        Returns:
            str: The formatted prompt.
        """
        prompt_template = PromptTemplate.from_template(interview_user_prompt)
        prompt = prompt_template.format(
            context=context,
            history=self.history,
        )
        return prompt

    def create_evaluation_prompt(self) -> str:
        """
        Create the prompt for generating an evaluation of the interview conversation.

        Returns:
            str: The formatted evaluation prompt.
        """
        prompt_template = PromptTemplate.from_template(evaluation_user_prompt)
        prompt = prompt_template.format(history=self.history)
        return prompt

    def update_history(self, text: str, role: str) -> None:
        """
        Update the conversation history with a new message.

        Args:
            text (str): Message content.
            role (str): Role of the sender (e.g., 'User', 'Chatbot', 'AI').
        """
        self.history += f"{role}: {text}\n"

    def get_context(self) -> str:
        """
        Retrieve relevant context via a similarity search on the conversation history.

        Returns:
            str: Concatenated context string.
        """
        results = self.vectorstore.similarity_search(self.history, k=1)
        context = "\n".join([doc.page_content for doc in results])
        return context

    def generate_question(self, user_input: str) -> str:
        """
        Generate a new interview question based on the candidate's input.

        Args:
            user_input (str): Candidate input text.

        Returns:
            str: Generated interview question.
        """
        if self.question_count > self.max_questions:
            return None
        else:
            context = self.get_context()
            self.update_history(user_input, "Candidate")
            prompt = self.create_question_prompt(context)
            response = self.call_llm(prompt, interview_system_prompt, stopwords=["Candidate:", f"\n{self.candidate_info['name']}", "(Note"])

        self.update_history(response, "Interviewer")
        self.question_count += 1
        return response

    def get_first_prompt(self) -> str:
        """
        Generate the initial greeting prompt.

        Returns:
            str: Greeting prompt.
        """
        return f"Hi, my name is {self.candidate_info['name']}, and I applied for the role of {self.candidate_info['role']}."

    def generate_evaluation(self) -> str:
        """
        Generate an evaluation of the interview conversation.

        Returns:
            str: Generated evaluation.
        """
        prompt = self.create_evaluation_prompt()
        response = self.call_llm(prompt, evaluation_system_prompt, stopwords=[])
        return response

    def save_interview(self, evaluation: str) -> None:
        """
        Save the complete interview session to the database.

        Args:
            evaluation (str): Evaluation text.
        """
        self.logger.info("Saving interview data.")
        interview = {
            "session_id": str(self.session_id),
            "user": json.dumps(self.candidate_info),
            "conversation": self.history,
            "evaluation": evaluation,
        }
        try:
            response = requests.post(f"{self.db_url}/log", json=interview, timeout=None)
            response.raise_for_status()
        except Exception as e:
            self.logger.error(f"Error saving interview data: {e}")
        self.logger.info(f"db response: {response}")
        self.logger.info("Interview data saved.")

    def process_llm_response(self, response: str) -> str:
        """
        Process the raw LLM response and trim extraneous content.

        Args:
            response (str): Raw response string.

        Returns:
            str: Processed response.
        """
        if response.startswith("Interviewer:"):
            response = response.split("Interviewer:")[1].strip()

        if ":\n\n" in response:
            response = response.split(":\n\n")[1].strip()
        return response

    def call_llm(self, prompt: str, system_prompt: str, stopwords: list) -> str:
        """
        Call the external LLM API with the provided prompt.

        Args:
            prompt (str): Prompt to send.

        Returns:
            str: Processed response from the LLM.
        """
        data = {
            "model": self.config["ollama"]["model"],
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config["ollama"]["temperature"],
                "top_p": self.config["ollama"]["top_p"],
                "stop": stopwords,
                "repeat_penalty": self.config["ollama"]["repeat_penalty"],
            }
        }
        self.logger.info(f"Calling LLM with payload: {data}")
        response = requests.post(f"{self.llm_url}/api/generate", json=data).json()
        self.logger.info(f"LLM response: {response}")
        processed = self.process_llm_response(response["response"])
        return processed
