'use client';

import { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, AlertCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { getPriceHistory, ApiError } from '@/lib/api';
import { PriceHistory, PriceSnapshot } from '@/lib/types';

interface PriceHistoryChartProps {
  propertyId: string;
  className?: string;
}

export function PriceHistoryChart({ propertyId, className }: PriceHistoryChartProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PriceHistory | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const history = await getPriceHistory(propertyId, 100);
        setData(history);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('Failed to load price history');
        }
      } finally {
        setLoading(false);
      }
    };

    if (propertyId) {
      fetchData();
    }
  }, [propertyId]);

  const chartData =
    data?.snapshots
      .slice()
      .reverse()
      .map((snapshot: PriceSnapshot) => ({
        date: new Date(snapshot.recorded_at).toLocaleDateString(),
        price: snapshot.price,
        pricePerSqm: snapshot.price_per_sqm,
      })) || [];

  const TrendIcon =
    data?.trend === 'increasing' ? TrendingUp : data?.trend === 'decreasing' ? TrendingDown : Minus;

  const trendColor =
    data?.trend === 'increasing'
      ? 'text-green-600'
      : data?.trend === 'decreasing'
        ? 'text-red-600'
        : 'text-gray-600';

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center h-64 text-center">
          <AlertCircle className="h-8 w-8 text-destructive mb-2" />
          <p className="text-destructive">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.snapshots.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Price History</CardTitle>
          <CardDescription>No price history available</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Price History</CardTitle>
            <CardDescription>{data.total} price snapshots recorded</CardDescription>
          </div>
          <div className={`flex items-center gap-2 ${trendColor}`}>
            <TrendIcon className="h-5 w-5" />
            <span className="font-medium capitalize">{data.trend}</span>
            {data.price_change_percent !== null && data.price_change_percent !== undefined && (
              <span className="text-sm">
                ({data.price_change_percent > 0 ? '+' : ''}
                {data.price_change_percent.toFixed(1)}%)
              </span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} tickLine={false} />
              <YAxis
                tick={{ fontSize: 12 }}
                tickLine={false}
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
              />
              <Tooltip
                formatter={(value: number) => [`$${value.toLocaleString()}`, 'Price']}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="price"
                stroke="#1f77b4"
                strokeWidth={2}
                dot={false}
                name="Price"
              />
              {chartData[0]?.pricePerSqm && (
                <Line
                  type="monotone"
                  dataKey="pricePerSqm"
                  stroke="#2ca02c"
                  strokeWidth={2}
                  dot={false}
                  name="Price/sqm"
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t">
          <div>
            <p className="text-sm text-muted-foreground">Current Price</p>
            <p className="text-lg font-semibold">
              {data.current_price ? `$${data.current_price.toLocaleString()}` : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">First Recorded</p>
            <p className="text-lg">
              {data.first_recorded ? new Date(data.first_recorded).toLocaleDateString() : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Price Change</p>
            <p className={`text-lg font-semibold ${trendColor}`}>
              {data.price_change_percent !== null && data.price_change_percent !== undefined
                ? `${data.price_change_percent > 0 ? '+' : ''}${data.price_change_percent.toFixed(1)}%`
                : 'N/A'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
