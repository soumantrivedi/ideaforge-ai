import { useState, useEffect } from 'react';
import { X, Users, Share2, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

import { getValidatedApiUrl } from '../lib/runtime-config';
const API_URL = getValidatedApiUrl();

interface ProductShareModalProps {
  productId: string;
  isOpen: boolean;
  onClose: () => void;
  onShareSuccess?: () => void;
}

interface User {
  id: string;
  email: string;
  full_name?: string;
}

interface Share {
  id: string;
  shared_with_user_id: string;
  permission: string;
  user_email: string;
  user_name?: string;
}

export function ProductShareModal({
  productId,
  isOpen,
  onClose,
  onShareSuccess,
}: ProductShareModalProps) {
  const { token, user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [shares, setShares] = useState<Share[]>([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [permission, setPermission] = useState<'view' | 'edit' | 'admin'>('view');
  const [isLoading, setIsLoading] = useState(false);
  const [isSharing, setIsSharing] = useState(false);

  useEffect(() => {
    if (isOpen && token) {
      loadUsers();
      loadShares();
    }
  }, [isOpen, token, productId]);

  const loadUsers = async () => {
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/auth/users`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        // Filter out current user - ensure users is an array
        const usersList = Array.isArray(data.users) ? data.users : [];
        setUsers(usersList.filter((u: User) => u.id !== user?.id));
      }
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadShares = async () => {
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/products/${productId}/shares`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setShares(data.shares || []);
      }
    } catch (error) {
      console.error('Failed to load shares:', error);
    }
  };

  const handleShare = async () => {
    if (!token || !selectedUserId) return;

    setIsSharing(true);
    try {
      const response = await fetch(`${API_URL}/api/products/${productId}/share`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          shared_with_user_id: selectedUserId,
          permission,
        }),
      });

      if (response.ok) {
        setSelectedUserId('');
        setPermission('view');
        loadShares();
        onShareSuccess?.();
      } else {
        const data = await response.json();
        alert(data.detail || 'Failed to share product');
      }
    } catch (error) {
      alert('Failed to share product');
    } finally {
      setIsSharing(false);
    }
  };

  const handleRemoveShare = async (shareId: string) => {
    if (!token || !confirm('Remove this share?')) return;

    try {
      const response = await fetch(`${API_URL}/api/products/${productId}/shares/${shareId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        loadShares();
        onShareSuccess?.();
      } else {
        alert('Failed to remove share');
      }
    } catch (error) {
      alert('Failed to remove share');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center gap-3">
            <Share2 className="w-6 h-6 text-blue-600" />
            <h3 className="text-xl font-bold text-gray-900">Share Product</h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Share with new user */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-4">Share with User</h4>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select User
                </label>
                <select
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Choose a user...</option>
                  {Array.isArray(users) && Array.isArray(shares) && users
                    .filter((u) => !shares.some((s) => s.shared_with_user_id === u.id))
                    .map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name || u.email}
                      </option>
                    ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Permission
                </label>
                <select
                  value={permission}
                  onChange={(e) => setPermission(e.target.value as 'view' | 'edit' | 'admin')}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="view">View Only</option>
                  <option value="edit">Can Edit</option>
                  <option value="admin">Admin Access</option>
                </select>
              </div>
              <button
                onClick={handleShare}
                disabled={!selectedUserId || isSharing}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
              >
                {isSharing ? 'Sharing...' : 'Share Product'}
              </button>
            </div>
          </div>

          {/* Existing shares */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-4">Shared With</h4>
            {shares.length === 0 ? (
              <p className="text-gray-500 text-sm">No shares yet</p>
            ) : (
              <div className="space-y-2">
                {shares.map((share) => (
                  <div
                    key={share.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <Users className="w-5 h-5 text-gray-500" />
                      <div>
                        <p className="font-medium text-gray-900">
                          {share.user_name || share.user_email}
                        </p>
                        <p className="text-sm text-gray-500 capitalize">{share.permission} access</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveShare(share.id)}
                      className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded-lg transition"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

