import { useState } from 'react';
import { MessageSquare, Calendar, Download, Trash2 } from 'lucide-react';

interface ConversationSession {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
  messageCount: number;
  phaseId?: string;
}

interface ConversationHistorySidebarProps {
  sessions: ConversationSession[];
  currentSessionId?: string;
  onSessionSelect: (sessionId: string) => void;
  onNewSession: () => void;
  onDeleteSession?: (sessionId: string) => void;
  onExportSession?: (sessionId: string) => void;
}

export function ConversationHistorySidebar({
  sessions,
  currentSessionId,
  onSessionSelect,
  onNewSession,
  onDeleteSession,
  onExportSession,
}: ConversationHistorySidebarProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <div className="h-full bg-white border-l border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onNewSession}
          className="w-full px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:from-blue-700 hover:to-purple-700 transition shadow-lg font-medium flex items-center justify-center gap-2"
        >
          <MessageSquare className="w-4 h-4" />
          New Conversation
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {sessions.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No conversations yet</p>
            <p className="text-xs mt-1">Start a new one to get going</p>
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.id === currentSessionId;
            const isHovered = hoveredId === session.id;

            return (
              <div
                key={session.id}
                onMouseEnter={() => setHoveredId(session.id)}
                onMouseLeave={() => setHoveredId(null)}
                className="relative"
              >
                <button
                  onClick={() => onSessionSelect(session.id)}
                  className={`w-full p-3 rounded-xl border-2 transition text-left ${
                    isActive
                      ? 'bg-blue-50 border-blue-500 shadow-md'
                      : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-sm'
                  }`}
                >
                  <div className="flex items-start gap-2 mb-2">
                    <MessageSquare className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isActive ? 'text-blue-600' : 'text-gray-400'}`} />
                    <div className="flex-1 min-w-0">
                      <h4 className="font-semibold text-sm text-gray-900 truncate">
                        {session.title}
                      </h4>
                    </div>
                  </div>

                  <p className="text-xs text-gray-600 line-clamp-2 mb-2">
                    {session.lastMessage}
                  </p>

                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      <span>{new Date(session.timestamp).toLocaleDateString()}</span>
                    </div>
                    <span>{session.messageCount} messages</span>
                  </div>
                </button>

                {isHovered && (
                  <div className="absolute top-2 right-2 flex items-center gap-1">
                    {onExportSession && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onExportSession(session.id);
                        }}
                        className="p-1.5 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition shadow-sm"
                        title="Export"
                      >
                        <Download className="w-3 h-3 text-gray-600" />
                      </button>
                    )}
                    {onDeleteSession && !isActive && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm('Delete this conversation?')) {
                            onDeleteSession(session.id);
                          }
                        }}
                        className="p-1.5 bg-white border border-red-200 rounded-lg hover:bg-red-50 transition shadow-sm"
                        title="Delete"
                      >
                        <Trash2 className="w-3 h-3 text-red-600" />
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      <div className="p-4 border-t border-gray-200 bg-gray-50 text-xs text-gray-600">
        <div className="flex items-center justify-between">
          <span>Total Conversations</span>
          <span className="font-semibold text-gray-900">{sessions.length}</span>
        </div>
      </div>
    </div>
  );
}
