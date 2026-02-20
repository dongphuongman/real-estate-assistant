'use client';

import React from 'react';

import { HeartButton } from './heart-button';
import type { Property } from '@/lib/types';

interface PropertyCardProps {
  property: Property;
  showFavoriteButton?: boolean;
}

export function PropertyCard({ property, showFavoriteButton = true }: PropertyCardProps) {
  return (
    <div className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden">
      <div className="aspect-video w-full bg-muted relative">
        {property.images?.[0] ? (
          <img
            src={property.images[0]}
            alt={property.title || 'Property'}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
            Property image
          </div>
        )}

        {showFavoriteButton && property.id && (
          <div className="absolute top-2 right-2">
            <HeartButton propertyId={property.id} />
          </div>
        )}
      </div>

      <div className="p-6 space-y-2">
        <h3 className="text-2xl font-semibold leading-none tracking-tight">
          {property.title || 'Untitled Property'}
        </h3>
        <p className="text-sm text-muted-foreground">
          {property.city}
          {property.country ? `, ${property.country}` : ''}
        </p>
        <div className="font-bold text-lg">
          {property.price ? `$${property.price.toLocaleString()}` : 'Price on request'}
        </div>
        <p className="text-sm text-muted-foreground">
          {[
            property.rooms ? `${property.rooms} beds` : null,
            property.bathrooms ? `${property.bathrooms} baths` : null,
            property.area_sqm ? `${property.area_sqm} m\u00B2` : null,
          ]
            .filter(Boolean)
            .join(' \u2022 ')}
        </p>
      </div>
    </div>
  );
}
