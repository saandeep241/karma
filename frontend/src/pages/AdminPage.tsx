import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAllUserTokenLimits, updateUserTokenLimit, resetUserTokenUsage } from '../api/client';

interface UserTokenLimit {
  user_id: string;
  monthly_limit: number;
  tokens_used_this_month: number;
  tokens_remaining: number;
  usage_percentage: number;
  current_month: string;
  last_reset_at: string;
  usage_stats: {
    total_tokens: number;
    request_count: number;
    by_agent: Record<string, { tokens: number; count: number }>;
    by_model: Record<string, { tokens: number; count: number }>;
  };
}

export function AdminPage() {
  const queryClient = useQueryClient();
  const [editingLimit, setEditingLimit] = useState<string | null>(null);
  const [newLimit, setNewLimit] = useState<string>('');

  // Fetch all user token limits
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin', 'token-limits'],
    queryFn: getAllUserTokenLimits,
    retry: false,
  });

  // Update limit mutation
  const updateLimitMutation = useMutation({
    mutationFn: ({ userId, limit }: { userId: string; limit: number }) =>
      updateUserTokenLimit(userId, limit),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'token-limits'] });
      setEditingLimit(null);
      setNewLimit('');
    },
  });

  // Reset usage mutation
  const resetUsageMutation = useMutation({
    mutationFn: (userId: string) => resetUserTokenUsage(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'token-limits'] });
    },
  });

  const handleUpdateLimit = (userId: string) => {
    const limit = parseInt(newLimit);
    if (isNaN(limit) || limit < 0) {
      alert('Please enter a valid number');
      return;
    }
    updateLimitMutation.mutate({ userId, limit });
  };

  const handleResetUsage = (userId: string) => {
    if (confirm('Are you sure you want to reset this user\'s monthly token usage?')) {
      resetUsageMutation.mutate(userId);
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  const formatPercentage = (num: number) => {
    return num.toFixed(1);
  };

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h2 className="text-red-800 font-semibold mb-2">Access Denied</h2>
          <p className="text-red-600">
            {(error as any)?.message || 'You do not have admin access. Admin access required.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Admin: Token Usage Management</h1>
        <p className="text-gray-600">
          Manage token limits and usage for all users. Default limit: {data?.default_limit ? formatNumber(data.default_limit) : 'N/A'} tokens/month
        </p>
      </div>

      {isLoading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-[#0066cc]"></div>
          <p className="mt-4 text-gray-600">Loading user data...</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Monthly Limit
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Used This Month
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Remaining
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Usage %
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Requests (30d)
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data?.users && data.users.length > 0 ? (
                  data.users.map((userLimit: UserTokenLimit) => (
                    <tr key={userLimit.user_id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-mono text-gray-900">
                          {userLimit.user_id.substring(0, 12)}...
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {editingLimit === userLimit.user_id ? (
                          <div className="flex items-center gap-2">
                            <input
                              type="number"
                              value={newLimit}
                              onChange={(e) => setNewLimit(e.target.value)}
                              placeholder={userLimit.monthly_limit.toString()}
                              className="w-32 px-2 py-1 border border-gray-300 rounded text-sm"
                              min="0"
                            />
                            <button
                              onClick={() => handleUpdateLimit(userLimit.user_id)}
                              disabled={updateLimitMutation.isPending}
                              className="px-3 py-1 bg-[#0066cc] text-white rounded text-sm hover:bg-[#0052a3] disabled:opacity-50"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => {
                                setEditingLimit(null);
                                setNewLimit('');
                              }}
                              className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-gray-900">
                              {formatNumber(userLimit.monthly_limit)}
                            </span>
                            <button
                              onClick={() => {
                                setEditingLimit(userLimit.user_id);
                                setNewLimit(userLimit.monthly_limit.toString());
                              }}
                              className="text-[#0066cc] hover:text-[#0052a3] text-sm"
                              title="Edit limit"
                            >
                              ✏️
                            </button>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {formatNumber(userLimit.tokens_used_this_month)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className={`text-sm font-medium ${
                          userLimit.tokens_remaining < userLimit.monthly_limit * 0.1
                            ? 'text-red-600'
                            : userLimit.tokens_remaining < userLimit.monthly_limit * 0.3
                            ? 'text-yellow-600'
                            : 'text-green-600'
                        }`}>
                          {formatNumber(userLimit.tokens_remaining)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                userLimit.usage_percentage >= 90
                                  ? 'bg-red-500'
                                  : userLimit.usage_percentage >= 70
                                  ? 'bg-yellow-500'
                                  : 'bg-green-500'
                              }`}
                              style={{ width: `${Math.min(userLimit.usage_percentage, 100)}%` }}
                            />
                          </div>
                          <span className="text-sm text-gray-600">
                            {formatPercentage(userLimit.usage_percentage)}%
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {formatNumber(userLimit.usage_stats?.request_count || 0)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleResetUsage(userLimit.user_id)}
                            disabled={resetUsageMutation.isPending}
                            className="px-3 py-1 bg-yellow-500 text-white rounded hover:bg-yellow-600 disabled:opacity-50 text-xs"
                            title="Reset monthly usage"
                          >
                            Reset Usage
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                      No users found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data && data.users && data.users.length > 0 && (
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">Usage Summary</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-blue-700">Total Users: </span>
              <span className="font-semibold">{data.total_users}</span>
            </div>
            <div>
              <span className="text-blue-700">Total Tokens Used: </span>
              <span className="font-semibold">
                {formatNumber(
                  data.users.reduce((sum, u) => sum + u.tokens_used_this_month, 0)
                )}
              </span>
            </div>
            <div>
              <span className="text-blue-700">Average Usage: </span>
              <span className="font-semibold">
                {formatPercentage(
                  data.users.reduce((sum, u) => sum + u.usage_percentage, 0) / data.users.length
                )}
                %
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
