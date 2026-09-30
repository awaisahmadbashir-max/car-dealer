import { useLayoutEffect, useRef, useState } from "react";
import type { SubmitEvent } from "react";
import { BeatLoader } from "react-spinners";
import { Car, Send } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { PageLayout } from "../components/PageLayout";
import { ChatMessage } from "../components/ChatMessage";
import type { APIPaginatedResponse, Message } from "../types";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { conversationAPI } from "../api/conversation";

const GREETING =
  "Hi! Which car are you looking to buy?";

export function ChatPage() {
  const messagesScrollRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [message, setMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedConversationId = searchParams.get("conversationId")
    ? Number(searchParams.get("conversationId"))
    : undefined;

  const { data: messages = { data: [] as Message[] } } =
    useQuery<APIPaginatedResponse<Message>>({
      queryKey: ["messages", 1, 50, selectedConversationId],
      queryFn: () =>
        conversationAPI.getMessages({
          page: 1,
          limit: 50,
          conversation_id: selectedConversationId as number,
        }),
      enabled: !!selectedConversationId,
    });

  const savedMessages = [...messages.data].sort((a, b) =>
    a.created_at.localeCompare(b.created_at),
  );
  const visibleMessages = selectedConversationId
    ? savedMessages
    : [
        {
          id: 0,
          conversation_id: 0,
          role: "assistant" as const,
          content: GREETING,
          created_at: new Date(0).toISOString(),
        },
        ...savedMessages.filter((item) => item.role === "user"),
      ];

  useLayoutEffect(() => {
    const el = messagesScrollRef.current;
    if (!el) {
      return;
    }
    el.scrollTop = el.scrollHeight;
  }, [visibleMessages.length, isSending, selectedConversationId]);

  function startNewChat() {
    setMessage("");
    setError(null);
    queryClient.removeQueries({ queryKey: ["messages", 1, 50, undefined] });
    setSearchParams({});
  }

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();

    const content = message.trim();
    if (!content || isSending) {
      return;
    }

    const queryKey = ["messages", 1, 50, selectedConversationId] as const;
    queryClient.setQueryData(
      queryKey,
      (oldData: APIPaginatedResponse<Message> | undefined) => {
        return {
          ...(oldData ?? {
            page: 1,
            limit: 50,
            total_items: 0,
            total_pages: 0,
          }),
          data: [
            ...(oldData?.data ?? []),
            {
              content,
              role: "user",
              created_at: new Date().toISOString(),
            },
          ] as Message[],
        };
      },
    );

    setMessage("");
    setError(null);
    setIsSending(true);

    try {
      const { data } = await conversationAPI.createMessage({
        content,
        conversation_id: selectedConversationId,
      });

      if (data?.conversation_id) {
        const conversationKey = ["messages", 1, 50, data.conversation_id] as const;
        if (!selectedConversationId) {
          queryClient.setQueryData(conversationKey, {
            page: 1,
            limit: 50,
            total_items: 3,
            total_pages: 1,
            data: [
              {
                id: -1,
                conversation_id: data.conversation_id,
                role: "assistant",
                content: GREETING,
                created_at: new Date(0).toISOString(),
              },
              {
                id: -2,
                conversation_id: data.conversation_id,
                role: "user",
                content,
                created_at: new Date().toISOString(),
              },
              data,
            ],
          });
        }
        queryClient.removeQueries({ queryKey: ["messages", 1, 50, undefined] });
        setSearchParams({ conversationId: String(data.conversation_id) });
        await queryClient.invalidateQueries({ queryKey: conversationKey });
      }
    } catch (sendError) {
      console.error(sendError);
      setMessage(content);
      setError("Could not send that message. Please try again.");
      queryClient.setQueryData(
        queryKey,
        (oldData: APIPaginatedResponse<Message> | undefined) => {
          if (!oldData) {
            return oldData;
          }
          return {
            ...oldData,
            data: oldData.data.filter((item) => item.id),
          };
        },
      );
    } finally {
      setIsSending(false);
    }
  }

  return (
    <PageLayout
      title="Find a car"
      description="Tell the assistant which car you want. It will match a dealer from the catalog."
      action={
        <button
          type="button"
          onClick={startNewChat}
          className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
        >
          New chat
        </button>
      }
    >
      <div className="flex h-143 flex-col rounded-lg bg-white shadow">
        <div className="border-b border-gray-200 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-indigo-100">
              <Car className="h-5 w-5 text-indigo-600" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                Car dealer assistant
              </p>
              <p className="text-xs text-gray-500">
                Looks up cars and dealers from the catalog
              </p>
            </div>
          </div>
        </div>

        <div ref={messagesScrollRef} className="flex-1 overflow-y-auto p-4">
          <div className="flex flex-col space-y-4">
            {visibleMessages.map((item) => (
              <ChatMessage key={item.id ?? item.created_at} message={item} />
            ))}
            {isSending && (
              <div className="flex items-end justify-end">
                <div className="mx-2 rounded-lg rounded-br-none bg-indigo-50 px-3 py-1">
                  <BeatLoader size={10} />
                </div>
              </div>
            )}
          </div>
        </div>

        {error ? (
          <p className="px-4 pb-2 text-sm text-red-600" role="alert">
            {error}
          </p>
        ) : null}

        <form
          onSubmit={handleSubmit}
          className="flex items-center border-t border-gray-200 px-4 py-3"
        >
          <input
            type="text"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Which car are you looking to buy?"
            disabled={isSending}
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={isSending || !message.trim()}
            className="ml-3 inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-gray-300"
          >
            <Send className="mr-2 h-4 w-4" />
            Send
          </button>
        </form>
      </div>
    </PageLayout>
  );
}
