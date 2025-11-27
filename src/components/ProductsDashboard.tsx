import { useState, useEffect } from 'react';
import { Plus, Folder, Users, Clock, MoreVertical, Share2, Edit, Trash2, ExternalLink } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { ProductShareModal } from './ProductShareModal';

import { getValidatedApiUrl } from '../lib/runtime-config';
const API_URL = getValidatedApiUrl();

interface Product {
  id: string;
  name: string;
  description?: string;
  status: string;
  user_id: string;
  owner_email: string;
  owner_name?: string;
  created_at: string;
  updated_at: string;
  access_level: string;
}

interface ProductsDashboardProps {
  onProductSelect?: (productId: string) => void;
  compact?: boolean;
}

export function ProductsDashboard({ onProductSelect, compact = false }: ProductsDashboardProps) {
  const { token } = useAuth();
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [newProductName, setNewProductName] = useState('');
  const [newProductDescription, setNewProductDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  const [shareProductId, setShareProductId] = useState<string | null>(null);
  const [showMenuFor, setShowMenuFor] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      loadProducts();
    }
  }, [token]);

  const loadProducts = async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/products`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setProducts(Array.isArray(data.products) ? data.products : []);
      }
    } catch (error) {
      console.error('Failed to load products:', error);
      setProducts([]); // Ensure products is always an array even on error
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !newProductName.trim()) return;

    setIsCreating(true);
    try {
      const response = await fetch(`${API_URL}/api/products`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          name: newProductName,
          description: newProductDescription || null,
        }),
      });

      if (response.ok) {
        setShowCreateModal(false);
        setNewProductName('');
        setNewProductDescription('');
        loadProducts();
      } else {
        const data = await response.json();
        alert(data.detail || 'Failed to create product');
      }
    } catch (error) {
      alert('Failed to create product');
    } finally {
      setIsCreating(false);
    }
  };

  const handleEditProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !editingProduct || !newProductName.trim()) return;

    setIsUpdating(true);
    try {
      const response = await fetch(`${API_URL}/api/products/${editingProduct.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          name: newProductName,
          description: newProductDescription || null,
        }),
      });

      if (response.ok) {
        setShowEditModal(false);
        setEditingProduct(null);
        setNewProductName('');
        setNewProductDescription('');
        loadProducts();
      } else {
        const data = await response.json();
        alert(data.detail || 'Failed to update product');
      }
    } catch (error) {
      alert('Failed to update product');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDeleteProduct = async (productId: string) => {
    if (!token || !confirm('Are you sure you want to delete this product? This action cannot be undone.')) {
      return;
    }

    setIsDeleting(productId);
    try {
      const response = await fetch(`${API_URL}/api/products/${productId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        credentials: 'include',
      });

      if (response.ok) {
        loadProducts();
      } else {
        const data = await response.json();
        alert(data.detail || 'Failed to delete product');
      }
    } catch (error) {
      alert('Failed to delete product');
    } finally {
      setIsDeleting(null);
      setShowMenuFor(null);
    }
  };

  const openEditModal = (product: Product) => {
    setEditingProduct(product);
    setNewProductName(product.name);
    setNewProductDescription(product.description || '');
    setShowEditModal(true);
    setShowMenuFor(null);
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, { bg: string; text: string; border: string }> = {
      ideation: { bg: 'var(--bg-tertiary)', text: 'var(--text-primary)', border: 'var(--border-color)' },
      build: { bg: 'var(--bg-tertiary)', text: 'var(--text-primary)', border: 'var(--border-color)' },
      operate: { bg: 'var(--bg-tertiary)', text: 'var(--text-primary)', border: 'var(--border-color)' },
      learn: { bg: 'var(--bg-tertiary)', text: 'var(--text-primary)', border: 'var(--border-color)' },
      govern: { bg: 'var(--bg-tertiary)', text: 'var(--text-primary)', border: 'var(--border-color)' },
      sunset: { bg: 'var(--bg-tertiary)', text: 'var(--text-primary)', border: 'var(--border-color)' },
    };
    return colors[status] || colors.ideation;
  };

  const getStatusLabel = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8" style={{ color: 'var(--text-secondary)' }}>
        <div>Loading products...</div>
      </div>
    );
  }

  // Ensure products is always an array
  const safeProducts = Array.isArray(products) ? products : [];

  return (
    <div className="space-y-6">
      {!compact && (
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>My Products</h2>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Manage your product lifecycle</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition flex items-center gap-2 font-medium"
          >
            <Plus className="w-5 h-5" />
            New Product
          </button>
        </div>
      )}

      {safeProducts.length === 0 ? (
        <div className="text-center py-16 rounded-xl border" style={{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--border-color)' }}>
          <Folder className="w-20 h-20 mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
          <h3 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>No products yet</h3>
          <p className="mb-6" style={{ color: 'var(--text-secondary)' }}>Create your first product to get started</p>
          {!compact && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium"
            >
              Create Product
            </button>
          )}
        </div>
      ) : (
        <div className={`grid gap-6 ${compact ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
          {safeProducts.length > 0 ? safeProducts.map((product) => {
            const statusColors = getStatusColor(product.status);
            const isOwner = product.access_level === 'owner';
            const isMenuOpen = showMenuFor === product.id;
            
            return (
              <div
                key={product.id}
                className={`rounded-xl border transition hover:shadow-lg ${compact ? 'p-4' : 'p-8'}`}
                style={{ 
                  backgroundColor: 'var(--card-bg)', 
                  borderColor: 'var(--border-color)',
                  minHeight: compact ? 'auto' : '280px'
                }}
              >
                <div className={`flex items-start justify-between ${compact ? 'mb-4' : 'mb-6'}`}>
                  <div className="flex-1 min-w-0">
                    <h3 className={`${compact ? 'text-lg' : 'text-2xl'} font-bold mb-2 truncate`} style={{ color: 'var(--text-primary)' }}>
                      {product.name}
                    </h3>
                    {product.description && !compact && (
                      <p className="text-sm mb-4 line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                        {product.description}
                      </p>
                    )}
                  </div>
                  {isOwner && (
                    <div className="relative ml-4">
                      <button
                        onClick={() => setShowMenuFor(isMenuOpen ? null : product.id)}
                        className="p-2 rounded-md transition"
                        style={{ color: 'var(--text-secondary)' }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'transparent';
                        }}
                      >
                        <MoreVertical className="w-5 h-5" />
                      </button>
                      {isMenuOpen && (
                        <div 
                          className="absolute right-0 mt-2 w-48 rounded-md border shadow-lg z-10"
                          style={{ 
                            backgroundColor: 'var(--card-bg)', 
                            borderColor: 'var(--border-color)' 
                          }}
                        >
                          <button
                            onClick={() => openEditModal(product)}
                            className="w-full px-4 py-2 text-left text-sm rounded-t-md transition flex items-center gap-2"
                            style={{ color: 'var(--text-primary)' }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.backgroundColor = 'transparent';
                            }}
                          >
                            <Edit className="w-4 h-4" />
                            Edit
                          </button>
                          <button
                            onClick={() => setShareProductId(product.id)}
                            className="w-full px-4 py-2 text-left text-sm transition flex items-center gap-2"
                            style={{ color: 'var(--text-primary)' }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.backgroundColor = 'transparent';
                            }}
                          >
                            <Share2 className="w-4 h-4" />
                            Share
                          </button>
                          <button
                            onClick={() => handleDeleteProduct(product.id)}
                            disabled={isDeleting === product.id}
                            className="w-full px-4 py-2 text-left text-sm rounded-b-md transition flex items-center gap-2"
                            style={{ color: 'var(--text-primary)' }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)';
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.backgroundColor = 'transparent';
                            }}
                          >
                            <Trash2 className="w-4 h-4" />
                            {isDeleting === product.id ? 'Deleting...' : 'Delete'}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className={`flex items-center gap-2 ${compact ? 'mb-4' : 'mb-6'}`}>
                  <span 
                    className="px-3 py-1 text-xs font-medium rounded-md border"
                    style={{ 
                      backgroundColor: statusColors.bg, 
                      color: statusColors.text,
                      borderColor: statusColors.border
                    }}
                  >
                    {getStatusLabel(product.status)}
                  </span>
                  {!isOwner && !compact && (
                    <span 
                      className="px-3 py-1 text-xs font-medium rounded-md border"
                      style={{ 
                        backgroundColor: 'var(--bg-tertiary)', 
                        color: 'var(--text-primary)',
                        borderColor: 'var(--border-color)'
                      }}
                    >
                      Shared
                    </span>
                  )}
                </div>

                {!compact && (
                  <div className="flex items-center justify-between text-sm mb-6" style={{ color: 'var(--text-tertiary)' }}>
                    <div className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      <span>{product.owner_name || product.owner_email}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      <span>{new Date(product.updated_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                )}

                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Open Product button clicked for product:', product.id, 'onProductSelect:', !!onProductSelect);
                    if (onProductSelect && product.id) {
                      try {
                          onProductSelect(product.id);
                      } catch (error) {
                        console.error('Error in onProductSelect:', error);
                        alert('Failed to open product. Please try again.');
                      }
                    } else {
                      console.warn('onProductSelect not available or product.id missing', { 
                        hasHandler: !!onProductSelect, 
                        productId: product.id 
                      });
                    }
                  }}
                  className="w-full px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium flex items-center justify-center gap-2"
                >
                  <ExternalLink className="w-4 h-4" />
                  {compact ? 'Select' : 'Open Product'}
                </button>
              </div>
            );
          }) : (
            <div className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>
              {isLoading ? 'Loading products...' : 'No products available'}
            </div>
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div 
          className="fixed inset-0 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
          onClick={() => setShowCreateModal(false)}
        >
          <div 
            className="rounded-xl shadow-xl max-w-md w-full p-6"
            style={{ backgroundColor: 'var(--card-bg)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Create New Product</h3>
            <form onSubmit={handleCreateProduct} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                  Product Name *
                </label>
                <input
                  type="text"
                  value={newProductName}
                  onChange={(e) => setNewProductName(e.target.value)}
                  required
                  className="w-full px-4 py-2 border rounded-md focus:ring-2 transition"
                  style={{ 
                    backgroundColor: 'var(--input-bg)', 
                    color: 'var(--text-primary)', 
                    borderColor: 'var(--input-border)' 
                  }}
                  placeholder="Enter product name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                  Description
                </label>
                <textarea
                  value={newProductDescription}
                  onChange={(e) => setNewProductDescription(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 border rounded-md focus:ring-2 transition"
                  style={{ 
                    backgroundColor: 'var(--input-bg)', 
                    color: 'var(--text-primary)', 
                    borderColor: 'var(--input-border)' 
                  }}
                  placeholder="Enter product description"
                />
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setNewProductName('');
                    setNewProductDescription('');
                  }}
                  className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 text-sm rounded-lg hover:bg-gray-300 transition font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating || !newProductName.trim()}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium disabled:opacity-50"
                >
                  {isCreating ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && editingProduct && (
        <div 
          className="fixed inset-0 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
          onClick={() => {
            setShowEditModal(false);
            setEditingProduct(null);
            setNewProductName('');
            setNewProductDescription('');
          }}
        >
          <div 
            className="rounded-xl shadow-xl max-w-md w-full p-6"
            style={{ backgroundColor: 'var(--card-bg)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Edit Product</h3>
            <form onSubmit={handleEditProduct} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                  Product Name *
                </label>
                <input
                  type="text"
                  value={newProductName}
                  onChange={(e) => setNewProductName(e.target.value)}
                  required
                  className="w-full px-4 py-2 border rounded-md focus:ring-2 transition"
                  style={{ 
                    backgroundColor: 'var(--input-bg)', 
                    color: 'var(--text-primary)', 
                    borderColor: 'var(--input-border)' 
                  }}
                  placeholder="Enter product name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
                  Description
                </label>
                <textarea
                  value={newProductDescription}
                  onChange={(e) => setNewProductDescription(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 border rounded-md focus:ring-2 transition"
                  style={{ 
                    backgroundColor: 'var(--input-bg)', 
                    color: 'var(--text-primary)', 
                    borderColor: 'var(--input-border)' 
                  }}
                  placeholder="Enter product description"
                />
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false);
                    setEditingProduct(null);
                    setNewProductName('');
                    setNewProductDescription('');
                  }}
                  className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 text-sm rounded-lg hover:bg-gray-300 transition font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUpdating || !newProductName.trim()}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium disabled:opacity-50"
                >
                  {isUpdating ? 'Updating...' : 'Update'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {shareProductId && (
        <ProductShareModal
          productId={shareProductId}
          isOpen={!!shareProductId}
          onClose={() => setShareProductId(null)}
          onShareSuccess={() => {
            loadProducts();
            setShareProductId(null);
          }}
        />
      )}
    </div>
  );
}
