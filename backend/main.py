from pathlib import Path
import subprocess
import tempfile

import ollama
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
4. For binary search on an input vector:
   time is O(log n), auxiliary space is O(1)
   when implemented iteratively with constant extra variables.
5. For nested loops, multiply iteration counts.
   If the inner variable doubles each iteration, its count is O(log n).
   Therefore n outer iterations and log n inner iterations give
   O(n log n), not O(n^2).
6. For recursion, write the COMPLETE recurrence, including
   non-recursive work. Example:
   T(n) = 2T(n/2) + O(1) gives O(n) time.
7. Analyze recursion stack depth separately.
   If n is halved in each call, depth is O(log n).
   If each stack frame uses O(1) extra space, stack space is O(log n).
8. Attribute each allocated array to the function that creates it.
   A vector temp(n) requires O(n) auxiliary space.
9. Do not confuse the number of recursive calls with recursion depth.
10. Give each function's time and auxiliary space.
11. Give an overall complexity for the complete program.
12. State assumptions clearly and check the final answer for consistency.

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

    print(f"Calling Ollama for task: {task}", flush=True)

    try:
        response = ollama.chat(
            model="qwen2.5:3b",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            options={"num_predict": num_predict},
        )

        explanation = response["message"]["content"]
        print(f"Ollama response received for {task}!", flush=True)

        return explanation

    except Exception as error:
        print(f"Ollama error during {task}: {error}", flush=True)

        raise HTTPException(
            status_code=502,
            detail=(
                "Could not get a response from Ollama. "
                "Check that Ollama is running and qwen2.5:3b "
                "is installed."
            ),
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
            executable = folder / "main.exe"

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
        raise HTTPException(
            status_code=500,
            detail=f"Could not start the compiler: {error}",
        )
