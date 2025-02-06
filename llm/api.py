from fastapi import FastAPI
from llm.interview_chain import InterviewChain
from pydantic import BaseModel

app = FastAPI()
interview_chain = InterviewChain()

class CandidateInfo(BaseModel):
    name: str
    role: str
    email: str

class QuestionRequest(BaseModel):
    user_input: str

@app.post("/start")
async def start(request: CandidateInfo):
    user_input = f"Hi, my name is {request.name}, and I applied for the role of {request.role}. I am ready for the interview."
    interview_chain.add_candidate_info(
        name=request.name, 
        role=request.role,
        email=request.email
    )
    llm_response = interview_chain.generate_question(user_input)
    return {"question": llm_response["response"]}

@app.post("/generate_question")
async def generate_question(request: QuestionRequest):
    llm_response = interview_chain.generate_question(request.user_input)
    return {"question": llm_response["response"]}

@app.post("/generate_evaluation")
async def generate_evaluation():
    llm_response = interview_chain.generate_evaluation()
    interview_chain.save_interview(llm_response)
    return {"message": "Interview completed."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, reload=True)