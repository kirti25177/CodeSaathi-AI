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

const BACKEND_URL = "https://codesaathi-ai-n6c2.onrender.com";

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

  function readableError(value: unknown): string {
    if (typeof value === "string") return value;
    if (value instanceof Error) return value.message;
    if (value == null) return "Unknown error occurred.";

    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }

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
      const response = await fetch(`${BACKEND_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ code, language }),
      });

      const responseText = await response.text();
      let data: AnalysisResponse = {};

      if (responseText.trim()) {
        try {
          data = JSON.parse(responseText) as AnalysisResponse;
        } catch {
          throw new Error(
            `Unexpected backend response (${response.status}): ${responseText}`
          );
        }
      }

      if (!response.ok) {
        throw new Error(
          readableError(
            data.detail ?? data.message ?? data.explanation ?? errorMessage
          )
        );
      }

      if (
        typeof data.explanation !== "string" ||
        !data.explanation.trim()
      ) {
        throw new Error(
          "The backend responded, but no explanation was returned."
        );
      }

      setResult(data.explanation);
    } catch (error) {
      console.error(`${endpoint} error:`, error);

      if (error instanceof TypeError) {
        setResult(
          "Could not connect to the backend. Please check the Render service, " +
            "backend CORS settings, and your internet connection."
        );
      } else {
        setResult(`Error:\n\n${readableError(error)}`);
      }
    } finally {
      setIsLoading(false);
    }
  }

  function explainCode() {
    return requestAnalysis(
      "/explain",
      "Thinking... AI is explaining your code.",
      "Code explanation failed."
    );
  }

  function findBugs() {
    return requestAnalysis(
      "/find-bugs",
      "Checking your code for possible bugs...",
      "Bug analysis failed."
    );
  }

  function analyzeComplexity() {
    return requestAnalysis(
      "/complexity",
      "Analyzing time complexity and auxiliary space...",
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
          AI workspace
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

            <button onClick={analyzeComplexity} disabled={isLoading}>
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

      <footer>Built for curious minds. Powered by AI.</footer>
    </main>
  );
}

export default App;
