import { useState, useEffect } from 'react';
import { CheckSquare, Square, Calendar, MessageSquare, Users } from 'lucide-react';

import { getValidatedApiUrl } from '../lib/runtime-config';
const API_URL = getValidatedApiUrl();

interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  agent_roles: string[];
}

interface SessionSelectorProps {
  productId: string;
  selectedSessions: string[];
  onSelectionChange: (sessionIds: string[]) => void;
  token: string;
  multiSelect?: boolean;
}

export function SessionSelector({
  productId,
  selectedSessions,
  onSelectionChange,
  token,
  multiSelect = true,
}: SessionSelectorProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, [productId, token]);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/products/${productId}/sessions`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) throw new Error('Failed to load sessions');

      const data = await response.json();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error('Error loading sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSessionToggle = (sessionId: string) => {
    if (multiSelect) {
      if (selectedSessions.includes(sessionId)) {
        onSelectionChange(selectedSessions.filter((id) => id !== sessionId));
      } else {
        onSelectionChange([...selectedSessions, sessionId]);
      }
    } else {
      onSelectionChange([sessionId]);
    }
  };

  if (loading) {
    return (
      <div className="p-4 text-center text-gray-500">Loading sessions...</div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        <MessageSquare className="w-8 h-8 mx-auto mb-2 text-gray-400" />
        <p>No conversation sessions found for this product.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Users className="w-5 h-5" />
          Select Conversation Sessions
        </h3>
        {selectedSessions.length > 0 && (
          <span className="text-sm text-gray-600">
            {selectedSessions.length} selected
          </span>
        )}
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {sessions.map((session) => {
          const isSelected = selectedSessions.includes(session.id);
          return (
            <div
              key={session.id}
              onClick={() => handleSessionToggle(session.id)}
              className={`p-4 rounded-lg border-2 cursor-pointer transition ${
                isSelected
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-start gap-3">
                {multiSelect ? (
                  isSelected ? (
                    <CheckSquare className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  ) : (
                    <Square className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                  )
                ) : (
                  <div
                    className={`w-4 h-4 rounded-full border-2 flex-shrink-0 mt-1 ${
                      isSelected
                        ? 'border-blue-600 bg-blue-600'
                        : 'border-gray-300'
                    }`}
                  >
                    {isSelected && (
                      <div className="w-full h-full rounded-full bg-blue-600" />
                    )}
                  </div>
                )}

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-semibold text-gray-900 truncate">
                      {session.title || `Session ${session.id.substring(0, 8)}`}
                    </h4>
                  </div>

                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    <div className="flex items-center gap-1">
                      <MessageSquare className="w-4 h-4" />
                      <span>{session.message_count} messages</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      <span>
                        {new Date(session.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  {session.agent_roles && session.agent_roles.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {session.agent_roles.map((role) => (
                        <span
                          key={role}
                          className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs"
                        >
                          {role}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {selectedSessions.length === 0 && (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">
            Please select at least one session to continue.
          </p>
        </div>
      )}
    </div>
  );
}

