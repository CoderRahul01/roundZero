/**
 * QuestionDisplay - Question progress and text display
 * 
 * Features:
 * - Current question number and total
 * - Question text display
 * - Progress bar
 * - Real-time updates via WebSocket
 */

import React from 'react';

interface QuestionDisplayProps {
  currentQuestion: number;
  totalQuestions: number;
  questionText?: string;
  showProgress?: boolean;
}

const QuestionDisplay: React.FC<QuestionDisplayProps> = ({
  currentQuestion,
  totalQuestions,
  questionText,
  showProgress = true
}) => {
  // Calculate progress percentage
  const progressPercentage = (currentQuestion / totalQuestions) * 100;

  return (
    <div className="w-full">
      {/* Question counter */}
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-white font-semibold text-lg">Current Question</h3>
        <div className="flex items-center space-x-2">
          <span className="text-blue-400 font-bold text-xl">
            {currentQuestion}
          </span>
          <span className="text-gray-500">/</span>
          <span className="text-gray-400 text-lg">
            {totalQuestions}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      {showProgress && (
        <div className="mb-4">
          <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
          <div className="flex justify-between mt-1 text-xs text-gray-500">
            <span>Start</span>
            <span>{Math.round(progressPercentage)}% Complete</span>
            <span>End</span>
          </div>
        </div>
      )}

      {/* Question text */}
      {questionText && (
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0 mt-1">
              <span className="text-2xl">❓</span>
            </div>
            <div className="flex-1">
              <p className="text-gray-300 leading-relaxed">
                {questionText}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Question status indicators */}
      <div className="mt-3 flex items-center justify-between text-sm">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-green-500 rounded-full" />
          <span className="text-gray-400">
            {currentQuestion - 1} completed
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
          <span className="text-gray-400">
            In progress
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-gray-600 rounded-full" />
          <span className="text-gray-400">
            {totalQuestions - currentQuestion} remaining
          </span>
        </div>
      </div>
    </div>
  );
};

export default QuestionDisplay;
