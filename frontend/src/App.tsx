
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useState } from "react";
import Editor from "@monaco-editor/react";
import "./App.css";

type AnalysisResponse = {
  explanation?: string;
  detail?: unknown;
  message?: string;
};

function App() {
  const [language, setLanguage] = useState("cpp");

  const [code, setCode] = useState(
    "int arr[] = {4, 2, 7};\n" +
      "int largest = arr[0];\n\n" +
      "for (int i = 1; i < 3; i++) {\n" +
      "    if (arr[i] > largest) {\n" +
      "        largest = arr[i];\n" +
      "    }\n" +
      "}"
  );

  const [result, setResult] = useState(
    "Welcome to CodeSaathi AI! Select an action to start learning."
  );

  const [isLoading, setIsLoading] = useState(false);

  // Convert backend errors into readable messages
  function readableError(value: unknown): string {
    if (typeof value === "string") {
      return value;
    }

    if (value instanceof Error) {
      return value.message;
    }

    if (value === null || value === undefined) {
      return "Unknown error occurred.";
    }

    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }

  // Common function used by all three AI features
  async function requestAnalysis(
    endpoint: string,
    loadingMessage: string,
    errorMessage: string
  ) {
    if (!code.trim()) {
      setResult("Please enter some code first.");
      return;
    }

    setIsLoading(true);
    setResult(loadingMessage);

    try {
      const response = await fetch(
  `https://codesaathi-ai-n6c2.onrender.com${endpoint}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ code, language }),
        }
      );

      // Read the response safely, even if the backend sends invalid JSON
      const responseText = await response.text();

      let data: AnalysisResponse = {};

      if (responseText.trim()) {
        try {
          data = JSON.parse(responseText) as AnalysisResponse;
        } catch {
          if (!response.ok) {
            throw new Error(
              `Backend returned an unexpected response (${response.status}): ${responseText}`
            );
          }

          throw new Error("Backend returned an invalid JSON response.");
        }
      }

      if (!response.ok) {
        const detail =
          data.detail ?? data.message ?? data.explanation ?? errorMessage;

        throw new Error(readableError(detail));
      }

      if (
        typeof data.explanation !== "string" ||
        !data.explanation.trim()
      ) {
        throw new Error(
          "The AI did not return an explanation. Check the backend response."
        );
      }

      setResult(data.explanation);
    } catch (error) {
      console.error(`${endpoint} Error:`, error);

      if (error instanceof TypeError) {
        setResult(
          "Could not connect to the backend.\n\n" +
            "Please check that FastAPI is running at http://127.0.0.1:8000 " +
            "and that the browser is not blocking the request."
        );
      } else {
        setResult(`Error:\n\n${readableError(error)}`);
      }
    } finally {
      setIsLoading(false);
    }
  }

  // Explain code using Ollama
  async function explainCode() {
    await requestAnalysis(
      "/explain",
      "Thinking... AI is explaining your code.",
      "Code explanation failed."
    );
  }

  // Find possible bugs using Ollama
  async function findBugs() {
    await requestAnalysis(
      "/find-bugs",
      "Checking your code for possible bugs...",
      "Bug analysis failed."
    );
  }

  // Analyze actual code complexity using Ollama
  async function analyzeComplexity() {
    await requestAnalysis(
      "/complexity",
      "Analyzing loops, recursion, time complexity and auxiliary space...",
      "Complexity analysis failed."
    );
  }

  const examples: Record<string, string> = {
    cpp: `int arr[] = {4, 2, 7};
int largest = arr[0];

for (int i = 1; i < 3; i++) {
    if (arr[i] > largest) {
        largest = arr[i];
    }
}

cout << largest;`,

    c: `#include <stdio.h>

int main() {
    int arr[] = {4, 2, 7};
    int largest = arr[0];

    for (int i = 1; i < 3; i++) {
        if (arr[i] > largest) {
            largest = arr[i];
        }
    }

    printf("%d", largest);
    return 0;
}`,

    java: `public class Main {
    public static void main(String[] args) {
        int[] arr = {4, 2, 7};
        int largest = arr[0];

        for (int i = 1; i < arr.length; i++) {
            if (arr[i] > largest) {
                largest = arr[i];
            }
        }

        System.out.println(largest);
    }
}`,
  };

  function changeLanguage(value: string) {
    setLanguage(value);
    setCode(examples[value] ?? "");
    setResult(
      `Language changed to ${value.toUpperCase()}. Select an action to continue.`
    );
  }

  return (
    <main className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-icon">&lt;/&gt;</span>
          <div>
            <h1>
              CodeSaathi <span>AI</span>
            </h1>
            <p>Your personal coding mentor</p>
          </div>
        </div>

        <div className="status">
          <span className="status-dot" />
          Local workspace
        </div>
      </header>

      <section className="welcome">
        <p className="eyebrow">LEARN BY UNDERSTANDING</p>
        <h2>
          Don't just write code. <span>Understand it.</span>
        </h2>
        <p>Explain code, find bugs and master DSA step by step.</p>
      </section>

      <section className="workspace">
        <div className="editor-panel">
          <div className="panel-header">
            <strong>Code Editor</strong>

            <select
              value={language}
              onChange={(e) => changeLanguage(e.target.value)}
              aria-label="Programming language"
              disabled={isLoading}
            >
              <option value="cpp">C++</option>
              <option value="c">C</option>
              <option value="java">Java</option>
            </select>
          </div>

          <Editor
            height="390px"
            language={language === "cpp" ? "cpp" : language}
            theme="vs-dark"
            value={code}
            onChange={(value) => setCode(value ?? "")}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              automaticLayout: true,
              scrollBeyondLastLine: false,
              padding: { top: 16 },
              readOnly: isLoading,
            }}
          />

          <div className="actions">
            <button onClick={explainCode} disabled={isLoading}>
              {isLoading ? "Analyzing..." : "Explain Code"}
            </button>

            <button onClick={findBugs} disabled={isLoading}>
              Find Bugs
            </button>

            <button
              onClick={analyzeComplexity}
              disabled={isLoading}
            >
              Analyze Complexity
            </button>
          </div>
        </div>

        <div className="result-panel">
          <div className="panel-header">
            <strong>Mentor's Explanation</strong>
            <span className="ai-label">AI MENTOR</span>
          </div>

          <div className="result-content markdown-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {result}
            </ReactMarkdown>
          </div>
        </div>
      </section>

      <footer>
        Built for curious minds. Powered by local AI.
      </footer>
    </main>
  );
}

export default App;
