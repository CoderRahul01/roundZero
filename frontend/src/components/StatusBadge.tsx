/**
 * StatusBadge - AI state indicator
 * 
 * Features:
 * - Color-coded states (listening/thinking/speaking/idle)
 * - Animated pulse effect
 * - Icon and text display
 */

import React from 'react';

interface StatusBadgeProps {
  state: 'idle' | 'listening' | 'thinking' | 'speaking';
  size?: 'sm' | 'md' | 'lg';
}

const StatusBadge: React.FC<StatusBadgeProps> = ({
  state,
  size = 'md'
}) => {
  // State configurations
  const stateConfig = {
    idle: {
      text: 'Idle',
      color: '#6b7280',
      bgColor: '#6b728020',
      icon: '⏸️',
      description: 'Waiting to start'
    },
    listening: {
      text: 'Listening',
      color: '#3b82f6',
      bgColor: '#3b82f620',
      icon: '👂',
      description: 'AI is listening to your answer'
    },
    thinking: {
      text: 'Thinking',
      color: '#8b5cf6',
      bgColor: '#8b5cf620',
      icon: '🤔',
      description: 'AI is analyzing your response'
    },
    speaking: {
      text: 'Speaking',
      color: '#10b981',
      bgColor: '#10b98120',
      icon: '🗣️',
      description: 'AI is speaking'
    }
  };

  // Size configurations
  const sizeConfig = {
    sm: {
      padding: 'px-2 py-1',
      text: 'text-xs',
      icon: 'text-sm',
      dot: 'w-2 h-2'
    },
    md: {
      padding: 'px-3 py-2',
      text: 'text-sm',
      icon: 'text-base',
      dot: 'w-3 h-3'
    },
    lg: {
      padding: 'px-4 py-3',
      text: 'text-base',
      icon: 'text-lg',
      dot: 'w-4 h-4'
    }
  };

  const config = stateConfig[state];
  const sizeStyles = sizeConfig[size];

  return (
    <div
      className={`inline-flex items-center space-x-2 rounded-full ${sizeStyles.padding} transition-all duration-300`}
      style={{
        backgroundColor: config.bgColor,
        border: `1px solid ${config.color}40`
      }}
      title={config.description}
    >
      {/* Animated pulse dot */}
      <div className="relative flex items-center justify-center">
        <div
          className={`${sizeStyles.dot} rounded-full ${state !== 'idle' ? 'animate-pulse' : ''}`}
          style={{ backgroundColor: config.color }}
        />
        {state !== 'idle' && (
          <div
            className={`absolute ${sizeStyles.dot} rounded-full animate-ping`}
            style={{ backgroundColor: config.color, opacity: 0.4 }}
          />
        )}
      </div>

      {/* Icon */}
      <span className={sizeStyles.icon}>{config.icon}</span>

      {/* Text */}
      <span
        className={`font-semibold ${sizeStyles.text}`}
        style={{ color: config.color }}
      >
        {config.text}
      </span>
    </div>
  );
};

export default StatusBadge;
