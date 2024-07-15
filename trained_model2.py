#sk-proj-C0tS9s0aRop9RDDydajPT3BlbkFJQmy71a2b15b85kRZ8MoC
import re
from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI



class CoffeeConversationModel:
    def __init__(self, model_name="gpt-3.5-turbo-instruct", openai_api_key="sk-proj-C0tS9s0aRop9RDDydajPT3BlbkFJQmy71a2b15b85kRZ8MoC"):
        self.model = OpenAI(model_name=model_name, temperature=0.0, openai_api_key=openai_api_key)
        self.json_prompt = PromptTemplate.from_template(
            "Return a JSON object with an `answer` key that answers the following question: {question}"
        )
        #, max_tokens=50
        self.chat = ChatOpenAI(model="gpt-3.5-turbo-1106", temperature=0.2, openai_api_key=openai_api_key)
        self.json_parser = SimpleJsonOutputParser()
        self.json_chain = self.json_prompt | self.model | self.json_parser

    def analyze_coffee_prompt(self, prompt):
        questions = {
            "is_about_coffee": "Based on the text, determine if the discussion is about coffee. Text: '{}'"
        }

        results = {}
        coffee_question = questions["is_about_coffee"].format(prompt)
        print(f"Question sent to model: {coffee_question}")  # Debugging output

        # Determine if the text is about coffee
        coffee_answer = list(self.json_chain.stream({"question": coffee_question}))[-1]
        print(f"Model's response: {coffee_answer}")  # Debugging output

        results["isAboutCoffee"] = coffee_answer.get('answer', 'no').strip().lower() == 'yes'

        # Check for explicit mentions of sugar and milk preferences
        results["sugarPreference"] = self.check_for_preference(prompt, 'sugar')
        results["milkPreference"] = self.check_for_preference(prompt, 'milk')

        return results

    def check_for_preference(self, text, item):
        positive_pattern = rf"\bwith {item}\b"
        negative_pattern = rf"\bno {item}\b|\bwithout {item}\b"

        if re.search(negative_pattern, text, re.IGNORECASE):
            return 'false'
        elif re.search(positive_pattern, text, re.IGNORECASE):
            return 'true'
        return 'not specified'

    def generate_response(self, prompt, results):

        context = f"You said: '{prompt}'\n"

        if results["isAboutCoffee"]:
            context += " Coffee mentioned."
        if results["sugarPreference"] != "not specified":
            context += f" Sugar preference: {'Yes' if results['sugarPreference'] == 'true' else 'No'}."
        if results["milkPreference"] != "not specified":
            context += f" Milk preference: {'Yes' if results['milkPreference'] == 'true' else 'No'}."

        context += "\nLimit response to three short sentences"


        return self.chat.invoke(input= context)