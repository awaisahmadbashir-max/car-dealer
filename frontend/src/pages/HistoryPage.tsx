import { useState } from "react";
import { PageLayout } from "../components/PageLayout";
import { HistoryTable } from "../components/HistoryTable";
import { useQuery } from "@tanstack/react-query";
import type { APIPaginatedResponse, Conversation } from "../types";
import { conversationAPI } from "../api/conversation";

export function HistoryPage() {
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(5);

  const {
    data: conversations = {
      data: [],
      page: 1,
      limit: 5,
      total_items: 0,
      total_pages: 0,
    },
  } = useQuery<APIPaginatedResponse<Conversation>>({
    queryKey: ["conversations", page, limit],
    queryFn: () =>
      conversationAPI.getConversations({
        page,
        limit,
      }),
  });

  return (
    <PageLayout
      title="Chat History"
      description="Past conversations are saved with each message"
    >
      <HistoryTable
        conversations={conversations}
        page={page}
        limit={limit}
        setPage={setPage}
        setLimit={setLimit}
      />
    </PageLayout>
  );
}
