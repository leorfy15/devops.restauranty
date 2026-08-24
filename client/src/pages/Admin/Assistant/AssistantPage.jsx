import { useState } from "react";
import axios from "axios";
import { MdSmartToy } from "react-icons/md";

const url =
  process.env.REACT_APP_SERVER_URL ||
  window.location.origin;

function AssistantPage() {
  const [mode, setMode] = useState("devops");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // Stores the pending controlled action returned by the backend.
  // We only use this for the coupon confirmation workflow.
  const [pendingActionId, setPendingActionId] =
    useState(null);

  const addAssistantMessage = ({
    text,
    model = "deterministic",
    source = null,
  }) => {
    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        text,
        model,
        source,
        mode,
      },
    ]);
  };

  const confirmPendingCoupon = async () => {
    if (!pendingActionId) {
      addAssistantMessage({
        text:
          "There is no pending coupon action to confirm.",
        model: "deterministic",
        source: "discounts-service",
      });

      return;
    }

    try {
      const response = await axios.post(
        `${url}/api/assistant/app/coupons/confirm`,
        {
          actionId: pendingActionId,
        }
      );

      const coupon =
        response.data?.coupon || {};

      addAssistantMessage({
        text:
          `Coupon "${coupon.name || "unknown"}" was created successfully. ` +
          `Discount: ${coupon.discount || "unknown"}%. ` +
          `Valid from ${coupon.start || "unknown"} ` +
          `to ${coupon.end || "unknown"}.`,
        model: "deterministic",
        source: "discounts-service",
      });

      // The token is one-time use.
      setPendingActionId(null);
    } catch (error) {
      console.error(
        "Coupon confirmation failed:",
        error
      );

      addAssistantMessage({
        text:
          error.response?.data?.detail ||
          "Unable to confirm the coupon creation.",
        model: "error",
        source: "discounts-service",
      });
    }
  };

  const sendMessage = async () => {
    const trimmedMessage = message.trim();

    if (!trimmedMessage || loading) {
      return;
    }

    const userMessage = {
      role: "user",
      text: trimmedMessage,
    };

    setMessages((current) => [
      ...current,
      userMessage,
    ]);

    setMessage("");
    setLoading(true);

    try {
      // ===================================================
      // Controlled confirmation
      // ===================================================

      const confirmationWords = [
        "confirm",
        "confirmed",
        "yes",
        "yes confirm",
        "confirm it",
        "create it",
        "go ahead",
        "proceed",
      ];

      const isConfirmation =
        mode === "devops" &&
        pendingActionId &&
        confirmationWords.includes(
          trimmedMessage.toLowerCase()
        );

      if (isConfirmation) {
        await confirmPendingCoupon();
        return;
      }

      // ===================================================
      // Normal chat
      // ===================================================

      const endpoint =
        mode === "devops"
          ? "/api/assistant/chat"
          : "/api/assistant/model-chat";

      const response = await axios.post(
        `${url}${endpoint}`,
        {
          message: trimmedMessage,
        }
      );

      // ===================================================
      // Controlled coupon preparation
      // ===================================================

      if (
        response.data?.status ===
          "confirmation_required" &&
        response.data?.actionId
      ) {
        setPendingActionId(
          response.data.actionId
        );
      }

      const assistantMessage = {
        role: "assistant",

        text:
          response.data.answer ||
          response.data.message ||
          "The assistant returned no answer.",

        model:
          response.data.model ||
          "unknown",

        source:
          response.data.source ||
          null,

        mode,
      };

      setMessages((current) => [
        ...current,
        assistantMessage,
      ]);
    } catch (error) {
      console.error(
        "Assistant request failed:",
        error
      );

      const errorMessage = {
        role: "assistant",

        text:
          error.response?.data?.detail ||
          "Unable to contact the AI Assistant.",

        model: "error",

        source: null,

        mode,
      };

      setMessages((current) => [
        ...current,
        errorMessage,
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setPendingActionId(null);
  };

  const changeMode = (newMode) => {
    setMode(newMode);

    // Do not carry a pending controlled action
    // into Direct Llama mode.
    if (newMode !== "devops") {
      setPendingActionId(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 p-8">
      <div className="max-w-5xl mx-auto">

        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <MdSmartToy className="text-4xl text-primary-600" />

            <div>
              <h1 className="text-3xl font-bold text-slate-800">
                Restauranty AI Assistant
              </h1>

              <p className="text-slate-500">
                Ask questions about Restauranty,
                Kubernetes and your infrastructure.
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">

          <div className="p-4 border-b border-slate-200 flex items-center justify-between gap-4">

            <div className="flex gap-2">

              <button
                onClick={() =>
                  changeMode("devops")
                }
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
                  mode === "devops"
                    ? "bg-primary-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                DevOps Assistant
              </button>

              <button
                onClick={() =>
                  changeMode("llama")
                }
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${
                  mode === "llama"
                    ? "bg-primary-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                Ask Llama
              </button>

            </div>

            <button
              onClick={clearChat}
              className="text-sm text-slate-500 hover:text-slate-800"
            >
              Clear chat
            </button>

          </div>

          <div className="px-5 py-3 bg-slate-50 border-b border-slate-200">

            {mode === "devops" ? (
              <div>
                <p className="text-sm text-slate-600">
                  <strong>
                    DevOps mode:
                  </strong>{" "}
                  uses live Kubernetes,
                  Prometheus, Loki, Cowrie and
                  Restauranty application APIs.
                </p>

                {pendingActionId && (
                  <p className="text-sm text-amber-700 mt-2 font-medium">
                    A coupon creation is waiting
                    for confirmation. Type
                    {" "}
                    <strong>confirm</strong>
                    {" "}
                    to continue.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-slate-600">
                <strong>
                  Direct Llama mode:
                </strong>{" "}
                talk directly with the
                llama3.2:1b model for general
                questions and explanations.
              </p>
            )}

          </div>

          <div className="h-[520px] overflow-y-auto p-6 space-y-5">

            {messages.length === 0 && (
              <div className="h-full flex items-center justify-center">

                <div className="text-center max-w-lg">

                  <MdSmartToy className="text-6xl text-slate-300 mx-auto mb-4" />

                  <h2 className="text-xl font-semibold text-slate-700 mb-2">
                    How can I help?
                  </h2>

                  {mode === "devops" ? (
                    <div className="text-sm text-slate-500 space-y-1">

                      <p>
                        Try asking:
                      </p>

                      <p>
                        "Are all Restauranty pods healthy?"
                      </p>

                      <p>
                        "Which pod is using the most CPU?"
                      </p>

                      <p>
                        "Were there attacks on the honeypot?"
                      </p>

                      <p>
                        "How many menu items do we have?"
                      </p>

                      <p>
                        "Create a coupon called STUDENTS-20
                        for 20% from 25 August 2026 until
                        10 September 2026"
                      </p>

                    </div>
                  ) : (
                    <div className="text-sm text-slate-500">

                      <p>
                        Try asking:
                      </p>

                      <p>
                        "Explain Kubernetes HPA in simple terms."
                      </p>

                    </div>
                  )}

                </div>
              </div>
            )}

            {messages.map(
              (chatMessage, index) => (
                <div
                  key={index}
                  className={`flex ${
                    chatMessage.role ===
                    "user"
                      ? "justify-end"
                      : "justify-start"
                  }`}
                >

                  <div
                    className={`max-w-[75%] rounded-2xl px-5 py-4 ${
                      chatMessage.role ===
                      "user"
                        ? "bg-primary-600 text-white"
                        : "bg-slate-100 text-slate-800"
                    }`}
                  >

                    <p className="whitespace-pre-wrap text-sm leading-relaxed">
                      {chatMessage.text}
                    </p>

                    {chatMessage.role ===
                      "assistant" && (
                      <div className="flex flex-wrap gap-2 mt-3">

                        <span className="text-[10px] uppercase tracking-wide px-2 py-1 rounded-full bg-white border border-slate-200 text-slate-500">
                          {chatMessage.model}
                        </span>

                        {chatMessage.source && (
                          <span className="text-[10px] uppercase tracking-wide px-2 py-1 rounded-full bg-white border border-slate-200 text-slate-500">
                            {chatMessage.source}
                          </span>
                        )}

                      </div>
                    )}

                  </div>
                </div>
              )
            )}

            {loading && (
              <div className="flex justify-start">

                <div className="bg-slate-100 rounded-2xl px-5 py-4">
                  <p className="text-sm text-slate-500 animate-pulse">
                    Assistant is thinking...
                  </p>
                </div>

              </div>
            )}

          </div>

          <div className="border-t border-slate-200 p-4">

            <div className="flex gap-3">

              <textarea
                value={message}
                onChange={(event) =>
                  setMessage(
                    event.target.value
                  )
                }
                onKeyDown={handleKeyDown}
                rows="2"
                placeholder={
                  pendingActionId &&
                  mode === "devops"
                    ? 'Type "confirm" to create the coupon...'
                    : mode === "devops"
                    ? "Ask about Restauranty or the infrastructure..."
                    : "Ask Llama anything..."
                }
                className="flex-1 resize-none rounded-xl border border-slate-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />

              <button
                onClick={sendMessage}
                disabled={
                  loading ||
                  !message.trim()
                }
                className="px-6 rounded-xl bg-primary-600 text-white font-semibold hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                Send
              </button>

            </div>

            <p className="text-xs text-slate-400 mt-2">
              Press Enter to send ·
              Shift + Enter for a new line
            </p>

          </div>

        </div>
      </div>
    </div>
  );
}

export default AssistantPage;