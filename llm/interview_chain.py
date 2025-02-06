import json
from llm.config import interview_system_prompt, initial_interview_prompt_structure, evaluation_system_prompt, initial_evaluation_prompt_structure
from langchain_core.prompts import PromptTemplate
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import requests
import os


class InterviewChain:

    def __init__(self):
        self.llm = None
        self.llm_url = os.environ["OLLAMA_URL"]
        self.vectorstore = self.init_vectorstore()
        self.candidate_info = None
        self.history = None
        self.max_questions = 3
        self.question_count = 0

    def init_candidate_info(self):
        self.candidate_info = {
            "name": "",
            "role": "",
            "email": "",
        }
    
    def init_new_session(self):
        self.history = ""
        self.init_candidate_info()
        self.question_count = 0

    def init_vectorstore(self):
        embedding = HuggingFaceEmbeddings(model_name="artifacts/models/all-MiniLM-L6-v2")
        dir_loader = DirectoryLoader("artifacts/books", glob="**/*.txt", loader_cls=TextLoader)
        docs = dir_loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = splitter.split_documents(docs)
        vectorstore = FAISS.from_documents(docs, embedding)
        return vectorstore
    
    def add_candidate_info(self, name, role, email):
        self.candidate_info["name"] = name
        self.candidate_info["role"] = role
        self.candidate_info["email"] = email

    def create_question_prompt(self, context, user_input):
        prompt = interview_system_prompt + initial_interview_prompt_structure
        
        prompt_template = PromptTemplate.from_template(prompt)
        prompt = prompt_template.format(
            context=context,
            history=self.history,
            input=user_input,
        )

        return prompt
    
    def create_evaluation_prompt(self):

        prompt = evaluation_system_prompt + initial_evaluation_prompt_structure

        prompt_template = PromptTemplate.from_template(prompt)
        prompt = prompt_template.format(
            history=self.history,
        )

        return prompt
    
    def create_finish_prompt(self):
        prompt = ""
        
        # prompt_template = PromptTemplate.from_template(prompt)
        # prompt = prompt_template.format(history=self.history)

        return prompt
    
    def update_history(self, text, role):
        self.history += f"{role}: {text}\n"

    def get_context(self):
        context = self.vectorstore.similarity_search(self.history, k=3)
        context = "\n".join([doc.page_content for doc in context])
        return context

    def generate_question(self, user_input):

        self.update_history(user_input, "User")
        context = self.get_context()

        prompt = self.create_question_prompt(context, user_input)
        response = self.call_llm(prompt)
        self.update_history(response, "Chatbot")

        self.question_count += 1
        
        return response
    
    def generate_evaluation(self):

        prompt = self.create_evaluation_prompt()

        response = self.call_llm(prompt)
        return response
    
    def finish_interview(self, user_input):
        self.update_history(user_input, "User")
        
        prompt = self.create_finish_prompt(user_input)
        response = self.call_llm(prompt)
        self.update_history(response, "Chatbot")

        return response
    
    def save_interview(self, evaluation):
        interview = {
            "candidate_info": self.candidate_info,
            "history": self.history,
            "evaluation": evaluation,
        }
        interview_filename = f'interview_{self.candidate_info["name"]}_{self.candidate_info["role"]}.json'.replace(" ", "_")
        with open("artifacts/interviews/" + interview_filename, "w") as f:
            json.dump(interview, f)

        return
    
    def call_llm(self, prompt):
        data = {
            "model": "llama3.2:1b",
            "prompt": prompt,
            "stream": False,
            "max_tokens": 200,
        }
        response = requests.post(f"{self.llm_url}/api/generate", json=data)
        return response.json()["response"]
