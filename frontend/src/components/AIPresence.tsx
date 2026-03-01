/**
 * AIPresence - Dynamic AI visualization component
 * 
 * Creates a living, breathing AI presence with:
 * - Audio waveform visualization
 * - Pulsing animations when speaking
 * - State-based visual feedback
 * - Smooth transitions
 */

import React, { useEffect, useRef, useState } from 'react';
import './AIPresence.css';

interface AIPresenceProps {
  aiState: 'idle' | 'listening' | 'thinking' | 'speaking';
  audioLevel?: number;
  isConnected: boolean;
}

const AIPresence: React.FC<AIPresenceProps> = ({ 
  aiState, 
  audioLevel = 0,
  isConnected 
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | undefined>(undefined);
  const [particles, setParticles] = useState<Array<{
    x: number;
    y: number;
    vx: number;
    vy: number;
    size: number;
    opacity: number;
  }>>([]);

  // Initialize particles
  useEffect(() => {
    const newParticles = Array.from({ length: 50 }, () => ({
      x: Math.random() * 400,
      y: Math.random() * 400,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: Math.random() * 3 + 1,
      opacity: Math.random() * 0.5 + 0.3
    }));
    setParticles(newParticles);
  }, []);

  // Animate canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw central orb
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      
      // Pulsing effect based on state
      const pulseSpeed = aiState === 'speaking' ? 0.05 : 0.02;
      const pulseSize = aiState === 'speaking' ? 20 : 10;
      const baseRadius = 80 + Math.sin(Date.now() * pulseSpeed) * pulseSize;

      // Outer glow
      const gradient = ctx.createRadialGradient(
        centerX, centerY, baseRadius * 0.5,
        centerX, centerY, baseRadius * 1.5
      );
      
      const stateColors = {
        idle: ['rgba(99, 102, 241, 0.3)', 'rgba(99, 102, 241, 0)'],
        listening: ['rgba(34, 197, 94, 0.4)', 'rgba(34, 197, 94, 0)'],
        thinking: ['rgba(251, 191, 36, 0.4)', 'rgba(251, 191, 36, 0)'],
        speaking: ['rgba(239, 68, 68, 0.5)', 'rgba(239, 68, 68, 0)']
      };

      gradient.addColorStop(0, stateColors[aiState][0]);
      gradient.addColorStop(1, stateColors[aiState][1]);

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius * 1.5, 0, Math.PI * 2);
      ctx.fill();

      // Main orb
      const mainGradient = ctx.createRadialGradient(
        centerX, centerY, 0,
        centerX, centerY, baseRadius
      );
      
      const mainColors = {
        idle: ['rgba(99, 102, 241, 0.8)', 'rgba(99, 102, 241, 0.3)'],
        listening: ['rgba(34, 197, 94, 0.9)', 'rgba(34, 197, 94, 0.4)'],
        thinking: ['rgba(251, 191, 36, 0.9)', 'rgba(251, 191, 36, 0.4)'],
        speaking: ['rgba(239, 68, 68, 1)', 'rgba(239, 68, 68, 0.5)']
      };

      mainGradient.addColorStop(0, mainColors[aiState][0]);
      mainGradient.addColorStop(1, mainColors[aiState][1]);

      ctx.fillStyle = mainGradient;
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius, 0, Math.PI * 2);
      ctx.fill();

      // Audio waveform when speaking
      if (aiState === 'speaking' && audioLevel > 0) {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.lineWidth = 3;
        ctx.beginPath();
        
        for (let i = 0; i < 360; i += 10) {
          const angle = (i * Math.PI) / 180;
          const waveOffset = Math.sin(Date.now() * 0.01 + i) * audioLevel * 20;
          const radius = baseRadius + waveOffset;
          const x = centerX + Math.cos(angle) * radius;
          const y = centerY + Math.sin(angle) * radius;
          
          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.closePath();
        ctx.stroke();
      }

      // Particles
      particles.forEach((particle, index) => {
        particle.x += particle.vx;
        particle.y += particle.vy;

        // Bounce off edges
        if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1;
        if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1;

        // Draw particle
        ctx.fillStyle = `rgba(255, 255, 255, ${particle.opacity})`;
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        ctx.fill();

        // Connect particles to center when speaking
        if (aiState === 'speaking') {
          const dx = centerX - particle.x;
          const dy = centerY - particle.y;
          const distance = Math.sqrt(dx * dx + dy * dy);
          
          if (distance < 150) {
            ctx.strokeStyle = `rgba(255, 255, 255, ${0.1 * (1 - distance / 150)})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(particle.x, particle.y);
            ctx.lineTo(centerX, centerY);
            ctx.stroke();
          }
        }
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [aiState, audioLevel, particles]);

  const stateLabels = {
    idle: 'Ready',
    listening: 'Listening...',
    thinking: 'Thinking...',
    speaking: 'Speaking...'
  };

  const stateIcons = {
    idle: '🤖',
    listening: '👂',
    thinking: '🤔',
    speaking: '💬'
  };

  return (
    <div className="ai-presence-container">
      <div className={`ai-presence-wrapper ${aiState}`}>
        <canvas 
          ref={canvasRef} 
          width={400} 
          height={400}
          className="ai-canvas"
        />
        
        <div className="ai-status-overlay">
          <div className="ai-status-icon">{stateIcons[aiState]}</div>
          <div className="ai-status-text">{stateLabels[aiState]}</div>
          {!isConnected && (
            <div className="ai-connection-status">Connecting...</div>
          )}
        </div>

        {aiState === 'speaking' && (
          <div className="audio-bars">
            {[...Array(5)].map((_, i) => (
              <div 
                key={i} 
                className="audio-bar"
                style={{
                  animationDelay: `${i * 0.1}s`,
                  height: `${20 + Math.random() * 60}%`
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AIPresence;
