from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm.interview_chain import InterviewChain

app = FastAPI()
interview_chain = InterviewChain()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CandidateInfo(BaseModel):
    name: str
    role: str
    email: str


class UserInput(BaseModel):
    user_input: str


@app.post("/start")
async def start(request: CandidateInfo):
    user_input = (
        f"Hi, my name is {request.name}, and I applied for the role of {request.role}. I am ready for the interview."
    )
    interview_chain.init_new_session()
    interview_chain.add_candidate_info(name=request.name, role=request.role, email=request.email)
    llm_response = interview_chain.generate_question(user_input)
    return {"question": llm_response}


@app.post("/generate_question")
async def generate_question(request: UserInput):
    if interview_chain.question_count > interview_chain.max_questions:
        llm_response = "Thank you for your time. The interview is now complete."
        return {"question": llm_response, "finish_interview": True}
    else:
        llm_response = interview_chain.generate_question(request.user_input)
        return {"question": llm_response}

@app.post("/generate_evaluation")
async def generate_evaluation():
    llm_response = interview_chain.generate_evaluation()
    interview_chain.save_interview(llm_response)
    return {"message": "Interview completed."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, reload=True)
