from fastapi import APIRouter ,  Depends
from llm.trained_model2 import CoffeeConversationModel
from app.models import PromptRequest


router = APIRouter()
ccm = CoffeeConversationModel()

class CoffeeConversationModelDependency:
    def __init__(self, ccm):
        self.ccm = ccm

    def __call__(self):
        return self.ccm


@router.post("/conversation")
async def get_response(message: PromptRequest,
                       ccm:CoffeeConversationModel =Depends(CoffeeConversationModelDependency(ccm))
                       ):
    res = ccm.analyze_coffee_prompt(message.prompt)
    response = ccm.generate_response(message.prompt, res)
    return {"results": res, "response": response}