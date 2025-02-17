import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm.interview_chain import InterviewChain

app = FastAPI()

config = yaml.safe_load(open("llm/config.yml"))
interview_chain = InterviewChain(config)

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
    try:
        user_input = f"Hi, my name is {request.name}, and I applied for the role of {request.role}. I am ready for the interview."
        interview_chain.init_new_session()
        interview_chain.add_candidate_info(name=request.name, role=request.role, email=request.email)
        llm_response = interview_chain.generate_question(user_input)
        if llm_response is None:
            raise HTTPException(status_code=500, detail="Failed to generate initial question.")
        return {"question": llm_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_question")
async def generate_question(request: UserInput):
    try:
        if interview_chain.question_count > interview_chain.max_questions:
            # If the number of asked questions exceeds the maximum,
            # end the interview and return a completion message.
            llm_response = "Thank you for your time. The interview is now complete."
            interview_chain.update_history(request.user_input, "Candidate")
            interview_chain.update_history(llm_response, "Interviewer")
            return {"question": llm_response, "finish_interview": True}
        else:
            # Generate a new question based on the user's input.
            llm_response = interview_chain.generate_question(request.user_input)
            if llm_response is None:
                raise HTTPException(status_code=500, detail="Failed to generate question.")
            return {"question": llm_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_evaluation")
async def generate_evaluation():
    """
    Generate an evaluation after the interview is complete.

    This endpoint calls the interview chain to generate an evaluation,
    saves the interview data, and returns a completion message.

    Returns:
        dict: A dictionary containing a message confirming interview completion.
    """
    try:
        llm_response = interview_chain.generate_evaluation()
        interview_chain.save_interview(llm_response)
        return {"message": "Interview completed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
