import { Bot, User } from "lucide-react";
import type { Message as ChatMessageType } from "../types";

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const isAssistant = message.role === "assistant";

  return (
    <div className={`flex items-end ${isAssistant ? "justify-end" : ""}`}>
      {!isAssistant && (
        <Avatar>
          <User className="h-4 w-4" />
        </Avatar>
      )}

      <div
        className={`mx-2 max-w-md whitespace-pre-line rounded-lg px-4 py-2 text-sm sm:max-w-lg ${
          isAssistant
            ? "rounded-br-none bg-indigo-500 text-white"
            : "rounded-bl-none bg-gray-100 text-gray-700"
        }`}
      >
        {message.content}
      </div>

      {isAssistant && (
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500 text-white">
          <Bot className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}

function Avatar({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-200 text-indigo-600">
      {children}
    </div>
  );
}
