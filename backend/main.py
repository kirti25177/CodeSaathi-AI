
import os
import subprocess
import tempfile
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="CodeSaathi AI")


# Request model shared by all API endpoints
class CodeRequest(BaseModel):
    code: str
    language: str = "cpp"


# Allow the React frontend to connect to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "https://code-saathi-ai.vercel.app",
        "https://code-saathi-ai-4qjz.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "CodeSaathi AI backend is running!"}


# Common function for all three AI features
def ask_ollama(code: str, language: str, task: str):
    if not code.strip():
        return "Please enter some code first."

    if task == "explain":
        system_prompt = """
You are CodeSaathi AI, a beginner-friendly coding mentor.

Explain the actual code step by step in simple language.
Explain important variables, conditions, loops, functions,
and dry runs where useful.

Do not invent behavior. Do not claim that you compiled or
executed the code.
"""
        user_prompt = (
            f"Programming language: {language}\n\n"
            f"Explain this code step by step:\n\n{code}"
        )
        num_predict = 1024

    elif task == "complexity":
        system_prompt = """
You are CodeSaathi AI, a precise DSA complexity analyzer.

Analyze the actual code mathematically. Never guess.

RULES:
1. Analyze every function separately.
2. Input arrays, vectors and strings are NOT auxiliary space.
   Do not count input storage as extra memory.
3. Count only additional memory allocated by the function.
4. Iterative binary search on an input vector takes O(log n)
   time and O(1) auxiliary space.
5. For nested loops, multiply iteration counts.
   If an inner variable doubles each iteration, its count is O(log n).
6. For recursion, write the complete recurrence, including
   non-recursive work.
7. Analyze recursion stack depth separately.
8. Attribute each allocated array to the function that creates it.
9. Do not confuse the number of recursive calls with recursion depth.
10. Give each function's time and auxiliary space.
11. Give an overall complexity for the complete program.
12. State assumptions clearly and check consistency.

Return a concise answer with these headings:
- Function-wise Time Complexity
- Function-wise Auxiliary Space
- Reasoning
- Overall Complexity

Do not claim that you compiled or executed the code.
"""
        user_prompt = (
            f"Language: {language}\n\n"
            "Analyze the following code. Include every function, "
            "correct loop counts, recursion recurrence relations, "
            "recursion stack space, and overall TC/SC.\n\n"
            f"CODE:\n{code}"
        )
        num_predict = 650

    elif task == "find-bugs":
        system_prompt = """
You are CodeSaathi AI, a careful programming mentor helping beginners
find bugs.

Review the code systematically for:
1. Syntax and compilation errors.
2. Array/vector bounds and off-by-one errors.
3. Incorrect assignments, comparisons, loops, and conditions.
4. Incorrect return values and calculations.
5. Data types, integer division, and overflow.
6. Edge cases and empty inputs.
7. Recursion errors and unnecessary repeated work.
8. Time and auxiliary space complexity when relevant.

For each likely issue, quote the relevant code, explain why it matters,
classify it as a compilation error, runtime risk, or logic bug,
and suggest a correction.

Do not invent bugs. If the code appears correct, say so.
Do not claim that you compiled or executed the code.
"""
        user_prompt = (
            f"Programming language: {language}\n\n"
            "Review every function in the following code. Identify "
            "possible issues, explain them, and suggest corrections.\n\n"
            f"CODE:\n{code}"
        )
        num_predict = 400

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported AI task: {task}",
        )

    # Read the secret from Render environment variables
    api_key = os.environ.get("OLLAMA_API_KEY")

    if not api_key:
        print("OLLAMA_API_KEY is not configured.", flush=True)
        raise HTTPException(
            status_code=500,
            detail="AI service is not configured. Please try again later.",
        )

    print(f"Calling Ollama Cloud for task: {task}", flush=True)

    try:
        response = requests.post(
            "https://ollama.com/api/chat",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-v4.1-flash",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                "stream": False,
                "options": {
                    "num_predict": num_predict,
                },
            },
            timeout=120,
        )

        response.raise_for_status()
        result = response.json()
        explanation = result["message"]["content"]

        print(
            f"Ollama Cloud response received for {task}!",
            flush=True,
        )

        return explanation

    except requests.exceptions.Timeout:
        print(f"Ollama Cloud timed out during {task}.", flush=True)
        raise HTTPException(
            status_code=504,
            detail="The AI service took too long to respond. Please try again.",
        )

    except requests.exceptions.HTTPError as error:
        status_code = (
            error.response.status_code
            if error.response is not None
            else 502
        )

        print(
            f"Ollama Cloud HTTP error during {task}: {status_code}",
            flush=True,
        )

        if status_code in (401, 403):
            detail = "AI authentication failed. Check the API key configuration."
        elif status_code == 429:
            detail = "AI service rate limit or quota reached. Please try again later."
        elif status_code == 404:
            detail = "The requested AI model was not found. Check the cloud model name."
        else:
            detail = "The AI provider returned an error. Please try again later."

        raise HTTPException(
            status_code=502,
            detail=detail,
        )

    except (requests.exceptions.RequestException, ValueError, KeyError) as error:
        print(
            f"Ollama Cloud error during {task}: {type(error).__name__}",
            flush=True,
        )
        raise HTTPException(
            status_code=502,
            detail="Could not get a valid response from the AI service.",
        )


# API 1: Explain Code
@app.post("/explain")
def explain_code(data: CodeRequest):
    print("Explain request received!", flush=True)

    explanation = ask_ollama(
        code=data.code,
        language=data.language,
        task="explain",
    )

    return {"explanation": explanation}


# API 2: Find Bugs
@app.post("/find-bugs")
def find_bugs(data: CodeRequest):
    print("Find Bugs request received!", flush=True)

    explanation = ask_ollama(
        code=data.code,
        language=data.language,
        task="find-bugs",
    )

    return {"explanation": explanation}


# API 3: Analyze Time and Space Complexity
@app.post("/complexity")
def analyze_complexity(data: CodeRequest):
    print("Complexity analysis request received!", flush=True)

    explanation = ask_ollama(
        code=data.code,
        language=data.language,
        task="complexity",
    )

    return {"explanation": explanation}


# API 4: Compile C++ code using G++
@app.post("/compile")
def compile_code(data: CodeRequest):
    code = data.code
    language = data.language

    if not code.strip():
        return {
            "success": False,
            "output": "Please enter some code first.",
        }

    if language != "cpp":
        return {
            "success": False,
            "output": "Compiler integration currently supports C++ only.",
        }

    if len(code) > 50000:
        raise HTTPException(
            status_code=413,
            detail=(
                "Code is too large to compile. "
                "Maximum size is 50,000 characters."
            ),
        )

    print("C++ compilation request received!", flush=True)

    try:
        with tempfile.TemporaryDirectory(
            prefix="codesaathi_"
        ) as temp_dir:
            folder = Path(temp_dir)
            source_file = folder / "main.cpp"
            executable = folder / "main"

            source_file.write_text(code, encoding="utf-8")

            result = subprocess.run(
                [
                    "g++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-pedantic",
                    str(source_file),
                    "-o",
                    str(executable),
                ],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=temp_dir,
                errors="replace",
            )

            compiler_output = (
                result.stderr.strip() or result.stdout.strip()
            )

            if result.returncode == 0:
                if compiler_output:
                    message = (
                        "Compilation successful. Compiler messages:\n\n"
                        + compiler_output
                    )
                else:
                    message = (
                        "Compilation successful! "
                        "No compiler warnings reported."
                    )

                return {
                    "success": True,
                    "output": message,
                }

            return {
                "success": False,
                "output": compiler_output or "Compilation failed.",
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "Compilation timed out after 10 seconds.",
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=(
                "G++ was not found. "
                "Check your compiler installation and PATH."
            ),
        )

    except OSError as error:
        print(f"Compiler OS error: {error}", flush=True)
        raise HTTPException(
            status_code=500,
            detail="Could not start the compiler.",
        )
