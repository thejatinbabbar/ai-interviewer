import json
import logging
import os

import requests
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings

from llm.prompts import evaluation_system_prompt, interview_system_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class InterviewChain:

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.llm_url = os.environ["OLLAMA_URL"]
        self.candidate_info = None
        self.history = None
        self.max_questions = self.config["max_questions"]
        self.question_count = 0
        self.vectorstore = self.init_vectorstore()

    def init_candidate_info(self):
        self.candidate_info = {
            "name": "",
            "role": "",
            "email": "",
        }

    def init_new_session(self):
        self.logger.info("Initializing new interview session.")
        self.history = ""
        self.init_candidate_info()
        self.question_count = 0

    def init_vectorstore(self):
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

    def add_candidate_info(self, name, role, email):
        self.candidate_info["name"] = name
        self.candidate_info["role"] = role
        self.candidate_info["email"] = email

    def create_question_prompt(self, context, user_input):
        prompt_template = PromptTemplate.from_template(interview_system_prompt)
        prompt = prompt_template.format(
            context=context,
            history=self.history,
        )
        return prompt

    def create_evaluation_prompt(self):
        prompt_template = PromptTemplate.from_template(evaluation_system_prompt)
        prompt = prompt_template.format(
            history=self.history,
        )
        return prompt

    def update_history(self, text, role):
        self.history += f"{role}: {text}\n"

    def get_context(self):
        context = self.vectorstore.similarity_search(self.history, k=3)
        context = "\n".join([doc.page_content for doc in context])
        return context

    def generate_question(self, user_input):

        self.update_history(user_input, "User")

        if self.question_count > self.max_questions:
            response = "End of conversation."
        else:
            context = self.get_context()
            prompt = self.create_question_prompt(context, user_input)
            response = self.call_llm(prompt)

        self.update_history(response, "Chatbot")

        self.question_count += 1

        return response

    def get_first_prompt(self):
        return f"""Hi, my name is {self.candidate_info["name"]}, and I applied for the role of {self.candidate_info["role"]}."""

    def generate_evaluation(self):
        prompt = self.create_evaluation_prompt()
        response = self.call_llm(prompt)
        return response

    def finish_interview(self, user_input):
        self.update_history(user_input, "User")
        prompt = self.create_finish_prompt(user_input)
        response = self.call_llm(prompt)
        self.update_history(response, "AI")
        return response

    def save_interview(self, evaluation):
        self.logger.info("Saving interview data.")
        interview = {
            "candidate_info": self.candidate_info,
            "history": self.history,
            "evaluation": evaluation,
        }
        interview_filename = f'interview_{self.candidate_info["name"]}_{self.candidate_info["role"]}.json'.replace(
            " ", "_"
        )
        with open("artifacts/interviews/" + interview_filename, "w") as f:
            json.dump(interview, f)
        self.logger.info(f"Interview data saved to {interview_filename}.")
        return

    def process_llm_response(self, response):
        response = response.split("?\n\n")[0]
        return response

    def call_llm(self, prompt):
        self.logger.info("Calling LLM with prompt: %s", prompt)
        data = {
            "model": self.config["ollama"]["model"],
            "prompt": prompt,
            "stream": False,
            "max_tokens": self.config["ollama"]["max_tokens"],
        }
        response = requests.post(f"{self.llm_url}/api/generate", json=data).json()["response"]
        response = self.process_llm_response(response)
        return response
