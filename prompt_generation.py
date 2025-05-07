import openai
import json
from if_testing import *
import os

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set. Please run `export OPENAI_API_KEY=your_key` in your terminal.")
openai.api_key = api_key

instructions_types = {
    "Keywords": {
        "Include Keyword": "Your response must contain the word {keyword}.",
        "Exclude Keyword": "Your response must NOT contain the word {keyword}.",
        "Keyword Frequency": "Your response must contain the word {keyword} {N} times.",
        "Keyword Frequency Floor": "Your response must use the word {keyword} at least {N} times.",
        "Keyword Order": "Your response must use the word {keyword_1} before the word {keyword_2} and must contain both.",
        "Keyword Pairings": "Your response must use the words {keyword_1} and {keyword_2} consecutively.",
        "First Occurence Keyword": "Your response must begin with the word {keyword_1}.",
        "Last Occurence Keyword": "Your response must end with the word {keyword_2}."
    },
    "Detectable Format": {
        "Title": "Your response must start with a title, wrapped in double angular brackets such as <<title>>.",
        "Letter/Email Format": "Your response must be written in the format of a letter, starting with Dear [recipient] and ending with Best Regards, [name].",
        "Schedule Format": "Your response must be written in the format of a schedule, as a list of (time, action) pairs.",
        "List Format": "Your response must be written in the form of a list, either bulleted or enumerated."
    },
    "Length Constraints": {
        "Maximum Words": "Your response must not exceed {N} words.",
        "Minimum Words": "Your response must be longer than {N} words."
    },
    "Change Cases": {
        "All Uppercase": "Your response must be written in all uppercase.",
        "All Lowercase": "Your response must be written in all lowercase."
    },
    "Start/End With": {
        "Start Checker": "Your response must start with the phrase {phrase}.",
        "End Checker": "Your response must end with the phrase {phrase}."
    }
}


def generate_context(instruction):
    prompt = f"""
    I am training a language model to generate diverse and creative prompt/instruction pairs for evaluating instruction-following abilities. Your task is to produce exactly two parts — and nothing more:

    1. **Context Sentence:**  
    Provide a unique, original, task-oriented, and diverse context for the given instruction. This context can take various forms

    2. **Verbatim Instruction:**  
    On a new line immediately after the context, include the EXACT instruction (word for word) as provided here:
    {instruction}

    Please ensure:
    - The first part (context sentence) is diverse and task oriented, meaning it should give an explicit task for a language model to complete. Remember, it should mimic real user queries
    - The instruction is reproduced exactly, with no modifications. If the instruction contains any curly brackets, replace them appropriately with a fitting word.
    - Do not include any extra text before, after, or between these two parts.

    Your response should consist solely of these two parts, separated by a newline.
    """
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.95,
        top_p=0.8,
        messages = [{"role" : "user", "content" : f"{prompt} Note that any time you need to make a new line, I want you to instead use //"}]
    )
    return response.choices[0].message.content

def generate_diverse_context(instruction):
    combined = "\n".join(f"{i+1}. {text}" for i, text in enumerate(instruction))
    prompt = f"""
    I am training a language model to generate diverse and creative prompt/instruction pairs for evaluating instruction-following abilities. Your task is to produce exactly two parts — and nothing more:

    1. **Context Sentence:**  
    Provide a unique, original, task-oriented, and diverse context for the given instruction. This context can take various forms

    2. **Verbatim Instruction:**  
    On a new line immediately after the context, include the EXACT instruction (word for word) as provided here:
    {combined}

    Please ensure:
    - The first part (context sentence) is diverse and task oriented, meaning it should give an explicit task for a language model to complete. Remember, it should mimic real user queries
    - The instruction is reproduced exactly, with no modifications. If the instruction contains any curly brackets, replace them appropriately with a fitting word.
    - Do not include any extra text before, after, or between these two parts.

    Your response should consist solely of these two parts, separated by a newline.
    """
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.9,
        messages = [{"role" : "user", "content" : prompt}]
    )
    return response.choices[0].message.content

def generate_prompt(instruction):
    prompt = generate_context(instruction)
    return prompt

def response_generation(prompt):
    response = openai.chat.completions.create(
        model="gpt-4o-mini", 
        messages = [{"role" : "user", "content" : f"{prompt} Note that whenever you need to write a new line, I want you to instead use //. Only include your response nothing before or after"}]
    )
    return response.choices[0].message.content

def main():
    diverse = int(input(f"Diverse: 1. Yes, 2. No \n"))
    points = int(input("How Many Datapoints: "))
    keys = list(instructions_types.keys())
    count, correct = 0, 0
    if diverse == 2:
        key = int(input(f"Type of Instruction given these types:  {list(enumerate(keys))}\n"))
        if key >= len(keys):
            raise NotImplementedError
        category = instructions_types[keys[key]]
        types = list(category.keys())
        selected = int(input(f"Kind of Instruction: {list(enumerate(types))}\n"))
        if selected >= len(types):
            raise NotImplementedError
        base_instruction = category[types[selected]]  # Keep this fixed

        for i in range(points):
            prompt = generate_prompt(base_instruction)
            response = response_generation(prompt)
            evaluated_instruction = make_instructions(prompt, response, i)
            res = evaluate(evaluated_instruction)
            if len(evaluated_instruction.instruction_id) > 0:
                count += 1
            if res:
                correct += 1
                with open("if_pairs.jsonl", 'a') as f:
                    json.dump(evaluated_instruction.__dict__, f)
                    f.write("\n")
    else:
        num_contexts = min(int(input("How many instructions would you like to use, 2 or 3 ")), 3)
        instructions = []
        for i in range(num_contexts):
            key = int(input(f"Type of Instruction given these types:  {list(enumerate(keys))}\n"))
            if key >= len(keys):
                raise NotImplementedError
            category = instructions_types[keys[key]]
            types = list(category.keys())
            selected = int(input(f"Kind of Instruction: {list(enumerate(types))}\n"))
            if selected >= len(types):
                raise NotImplementedError
            instructions.append(category[types[selected]])
        for i in range(points):
            prompt = generate_diverse_context(instructions)
            response = response_generation(prompt)
            instruction = make_instructions(prompt, response, i)
            res = evaluate(instruction)
            if len(instruction.instruction_id) == num_contexts:
                count += 1
            if res:
                correct += 1
                with open("if_pairs.jsonl", 'a') as f:
                    json.dump(instruction.__dict__, f)
                    f.write("\n")
    print(f"correct: {correct}, total: {count}")

if __name__ == "__main__":
    main()
