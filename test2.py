import openai

def test_generate():
    openai.api_key = 'your-api-key'  # Replace with your actual API key

    try:
        response = openai.ChatCompletion.create(
            model="text-davinci-002",  # Ensure this is the correct model name
            messages=[{"role": "user", "content": "What is the capital of France?"}],
            max_tokens=50
        )
        print("Response:", response)  # This will print the raw response to understand its structure
    except Exception as e:
        print("Error during API call:", str(e))

test_generate()
