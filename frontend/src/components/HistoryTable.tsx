import { ChevronLeft, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { APIPaginatedResponse, Conversation } from "../types";
import { formatDate } from "../utils/date";

const PAGE_SIZE_OPTIONS = [5, 10, 25] as const;

export function HistoryTable({
  conversations,
  page,
  limit,
  setPage,
  setLimit,
}: {
  conversations: APIPaginatedResponse<Conversation>;
  page: number;
  limit: number;
  setPage: (page: number) => void;
  setLimit: (limit: number) => void;
}) {
  const { total_items, total_pages, data } = conversations;
  const totalPages = Math.max(1, total_pages);
  const safePage = Math.min(Math.max(1, page), totalPages);
  const canPrev = safePage > 1;
  const canNext = safePage < totalPages;

  const from = total_items === 0 ? 0 : (safePage - 1) * limit + 1;
  const to = Math.min(safePage * limit, total_items);

  return (
    <div className="overflow-hidden rounded-lg bg-white shadow">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {["ID", "Last message", "Date/Time", ""].map((head) => (
                <th
                  key={head}
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                >
                  {head}
                </th>
              ))}
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-200 bg-white">
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="px-6 py-12 text-center text-sm text-gray-500"
                >
                  No conversations yet.
                </td>
              </tr>
            ) : (
              data.map((item) => {
                const chatPath = new URLSearchParams();
                chatPath.set("conversationId", item.id.toString());

                return (
                  <tr
                    key={item.id}
                    className="transition-colors hover:bg-gray-50"
                  >
                    <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                      #{item.id}
                    </td>
                    <td className="max-w-xs truncate px-6 py-4 text-sm text-gray-500">
                      {item.last_message?.content ?? "—"}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {item.last_message
                        ? formatDate(item.last_message.created_at)
                        : "—"}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                      <Link
                        to={`/chat?${chatPath.toString()}`}
                        className="text-indigo-600 hover:text-indigo-900"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-4 border-t border-gray-200 bg-gray-50 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="text-sm text-gray-600">
          {total_items === 0 ? (
            <>No conversations</>
          ) : (
            <>
              Showing <span className="font-medium text-gray-900">{from}</span>–
              <span className="font-medium text-gray-900">{to}</span> of{" "}
              <span className="font-medium text-gray-900">{total_items}</span>
            </>
          )}
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <span className="whitespace-nowrap">Rows per page</span>
            <select
              value={limit}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setPage(1);
              }}
              className="rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={!canPrev}
              onClick={() => setPage(safePage - 1)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-300 bg-white text-gray-700 shadow-sm hover:bg-gray-50 disabled:pointer-events-none disabled:opacity-40"
              aria-label="Previous page"
            >
              <ChevronLeft size={18} />
            </button>
            <span className="min-w-[5.5rem] px-2 text-center text-sm tabular-nums text-gray-700">
              Page {safePage} of {totalPages}
            </span>
            <button
              type="button"
              disabled={!canNext}
              onClick={() => setPage(safePage + 1)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-300 bg-white text-gray-700 shadow-sm hover:bg-gray-50 disabled:pointer-events-none disabled:opacity-40"
              aria-label="Next page"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
