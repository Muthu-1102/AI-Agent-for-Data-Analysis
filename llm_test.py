from groq import Groq

# Initialize client
client = Groq()

# Send request to LLaMA model
response = client.chat.completions.create(
    model="llama3-8b-8192",   # llama3-8b-8192 is currently supported; llama3-70b-8192 is deprecated
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain recursion in simple terms"}
    ],
    temperature=0.7,
    max_tokens=500
)

# Print output
print(response.choices[0].message.content)