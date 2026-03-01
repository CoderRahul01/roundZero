/**
 * ConfidenceMeter - Visual confidence score display
 * 
 * Features:
 * - Color-coded meter (red: 0-40, yellow: 41-70, green: 71-100)
 * - Smooth transitions
 * - Numeric score display
 */

import React from 'react';

interface ConfidenceMeterProps {
  score: number; // 0-100
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const ConfidenceMeter: React.FC<ConfidenceMeterProps> = ({
  score,
  showLabel = true,
  size = 'md'
}) => {
  // Clamp score to 0-100 range
  const clampedScore = Math.max(0, Math.min(100, score));

  // Determine color based on score
  const getColor = (score: number): string => {
    if (score >= 71) return '#10b981'; // green
    if (score >= 41) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };

  // Get label text based on score
  const getLabel = (score: number): string => {
    if (score >= 71) return 'High';
    if (score >= 41) return 'Medium';
    return 'Low';
  };

  // Size configurations
  const sizeConfig = {
    sm: { height: 'h-2', text: 'text-sm' },
    md: { height: 'h-4', text: 'text-base' },
    lg: { height: 'h-6', text: 'text-lg' }
  };

  const config = sizeConfig[size];
  const color = getColor(clampedScore);
  const label = getLabel(clampedScore);

  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex justify-between items-center mb-2">
          <span className="text-gray-400 text-sm">Confidence</span>
          <div className="flex items-center space-x-2">
            <span className={`text-white font-bold ${config.text}`}>
              {clampedScore}
            </span>
            <span className="text-gray-500 text-xs">/ 100</span>
          </div>
        </div>
      )}

      {/* Meter bar */}
      <div className={`w-full bg-gray-700 rounded-full ${config.height} overflow-hidden`}>
        <div
          className={`${config.height} rounded-full transition-all duration-500 ease-out`}
          style={{
            width: `${clampedScore}%`,
            backgroundColor: color
          }}
        />
      </div>

      {/* Labels */}
      {showLabel && (
        <div className="flex justify-between mt-1">
          <span className="text-xs text-gray-500">Low</span>
          <span className="text-xs text-gray-500">Medium</span>
          <span className="text-xs text-gray-500">High</span>
        </div>
      )}

      {/* Current level indicator */}
      {showLabel && (
        <div className="mt-2 text-center">
          <span
            className="inline-block px-3 py-1 rounded-full text-xs font-semibold"
            style={{
              backgroundColor: `${color}20`,
              color: color
            }}
          >
            {label} Confidence
          </span>
        </div>
      )}
    </div>
  );
};

export default ConfidenceMeter;
