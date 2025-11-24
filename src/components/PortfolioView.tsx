import { useState, useEffect } from 'react';
import { Building2, Users, Package, TrendingUp, Filter } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface PortfolioItem {
  id: string;
  name: string;
  description?: string;
  status: string;
  user_id: string;
  owner_email: string;
  owner_name?: string;
  created_at: string;
  updated_at: string;
  share_count: number;
  shared_with_me: boolean;
}

interface PortfolioViewProps {
  onProductSelect?: (productId: string) => void;
}

export function PortfolioView({ onProductSelect }: PortfolioViewProps) {
  const { user, token } = useAuth();
  const [portfolio, setPortfolio] = useState<PortfolioItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'mine' | 'shared'>('all');

  useEffect(() => {
    if (token) {
      loadPortfolio();
    }
  }, [token]);

  const loadPortfolio = async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/products/portfolio`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setPortfolio(data.portfolio || []);
      }
    } catch (error) {
      console.error('Failed to load portfolio:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredPortfolio = Array.isArray(portfolio) ? portfolio.filter((item) => {
    if (filter === 'mine') return item.user_id === user?.id;
    if (filter === 'shared') return item.shared_with_me;
    return true;
  }) : [];

  const stats = {
    total: Array.isArray(portfolio) ? portfolio.length : 0,
    mine: Array.isArray(portfolio) ? portfolio.filter((p) => p.user_id === user?.id).length : 0,
    shared: Array.isArray(portfolio) ? portfolio.filter((p) => p.shared_with_me).length : 0,
    byStatus: Array.isArray(portfolio) ? portfolio.reduce((acc, p) => {
      acc[p.status] = (acc[p.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>) : {},
  };

  const getStatusColor = (status: string) => {
    // Use theme-aware colors
    return 'px-2 py-1 text-xs font-medium rounded';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div style={{ color: 'var(--text-secondary)' }}>Loading portfolio...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Portfolio</h2>
          <p className="mt-1" style={{ color: 'var(--text-secondary)' }}>
            All products in {user?.tenant_name || 'your tenant'}
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-xl shadow p-6" style={{ backgroundColor: 'var(--card-bg)' }}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Total Products</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{stats.total}</p>
            </div>
            <Package className="w-8 h-8" style={{ color: 'var(--accent-color)' }} />
          </div>
        </div>
        <div className="rounded-xl shadow p-6" style={{ backgroundColor: 'var(--card-bg)' }}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>My Products</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{stats.mine}</p>
            </div>
            <Users className="w-8 h-8" style={{ color: 'var(--accent-color)' }} />
          </div>
        </div>
        <div className="rounded-xl shadow p-6" style={{ backgroundColor: 'var(--card-bg)' }}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Shared With Me</p>
              <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{stats.shared}</p>
            </div>
            <TrendingUp className="w-8 h-8" style={{ color: 'var(--accent-color)' }} />
          </div>
        </div>
        <div className="rounded-xl shadow p-6" style={{ backgroundColor: 'var(--card-bg)' }}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Tenant</p>
              <p className="text-lg font-bold truncate" style={{ color: 'var(--text-primary)' }}>
                {user?.tenant_name || 'N/A'}
              </p>
            </div>
            <Building2 className="w-8 h-8" style={{ color: 'var(--accent-color)' }} />
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        <Filter className="w-5 h-5" style={{ color: 'var(--text-tertiary)' }} />
        <button
          onClick={() => setFilter('all')}
          className="px-4 py-2 rounded-lg transition font-medium"
          style={{
            backgroundColor: filter === 'all' ? 'var(--button-primary-bg)' : 'var(--card-bg)',
            color: filter === 'all' ? 'var(--button-primary-text)' : 'var(--text-primary)',
            border: `1px solid ${filter === 'all' ? 'transparent' : 'var(--border-color)'}`
          }}
          onMouseEnter={(e) => {
            if (filter !== 'all') {
              e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
            }
          }}
          onMouseLeave={(e) => {
            if (filter !== 'all') {
              e.currentTarget.style.backgroundColor = 'var(--card-bg)';
            }
          }}
        >
          All
        </button>
        <button
          onClick={() => setFilter('mine')}
          className="px-4 py-2 rounded-lg transition font-medium"
          style={{
            backgroundColor: filter === 'mine' ? 'var(--button-primary-bg)' : 'var(--card-bg)',
            color: filter === 'mine' ? 'var(--button-primary-text)' : 'var(--text-primary)',
            border: `1px solid ${filter === 'mine' ? 'transparent' : 'var(--border-color)'}`
          }}
          onMouseEnter={(e) => {
            if (filter !== 'mine') {
              e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
            }
          }}
          onMouseLeave={(e) => {
            if (filter !== 'mine') {
              e.currentTarget.style.backgroundColor = 'var(--card-bg)';
            }
          }}
        >
          My Products
        </button>
        <button
          onClick={() => setFilter('shared')}
          className="px-4 py-2 rounded-lg transition font-medium"
          style={{
            backgroundColor: filter === 'shared' ? 'var(--button-primary-bg)' : 'var(--card-bg)',
            color: filter === 'shared' ? 'var(--button-primary-text)' : 'var(--text-primary)',
            border: `1px solid ${filter === 'shared' ? 'transparent' : 'var(--border-color)'}`
          }}
          onMouseEnter={(e) => {
            if (filter !== 'shared') {
              e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
            }
          }}
          onMouseLeave={(e) => {
            if (filter !== 'shared') {
              e.currentTarget.style.backgroundColor = 'var(--card-bg)';
            }
          }}
        >
          Shared With Me
        </button>
      </div>

      {/* Portfolio Grid */}
      {filteredPortfolio.length === 0 ? (
        <div className="text-center py-12 rounded-xl shadow" style={{ backgroundColor: 'var(--card-bg)' }}>
          <Package className="w-16 h-16 mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
          <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>No products found</h3>
          <p style={{ color: 'var(--text-secondary)' }}>Try adjusting your filters</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredPortfolio.map((item) => (
            <div
              key={item.id}
              className="rounded-xl shadow-lg p-6 hover:shadow-xl transition"
              style={{ backgroundColor: 'var(--card-bg)' }}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>{item.name}</h3>
                  {item.description && (
                    <p className="text-sm line-clamp-2" style={{ color: 'var(--text-secondary)' }}>{item.description}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 mb-4">
                <span 
                  className={getStatusColor(item.status)}
                  style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}
                >
                  {item.status}
                </span>
                {item.shared_with_me && (
                  <span className="px-2 py-1 text-xs font-medium rounded" style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}>
                    Shared
                  </span>
                )}
                {item.share_count > 0 && (
                  <span className="px-2 py-1 text-xs font-medium rounded" style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}>
                    {item.share_count} shares
                  </span>
                )}
              </div>

              <div className="flex items-center justify-between text-sm mb-4" style={{ color: 'var(--text-tertiary)' }}>
                <div className="flex items-center gap-1">
                  <Users className="w-4 h-4" />
                  <span>{item.owner_name || item.owner_email}</span>
                </div>
                <div className="text-xs">
                  {new Date(item.updated_at).toLocaleDateString()}
                </div>
              </div>

              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (onProductSelect && item.id) {
                    console.log('View Product clicked for:', item.id);
                    onProductSelect(item.id);
                  } else {
                    console.error('Cannot view product: onProductSelect or item.id missing', { onProductSelect: !!onProductSelect, itemId: item.id });
                  }
                }}
                className="w-full px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium"
              >
                View Product
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

