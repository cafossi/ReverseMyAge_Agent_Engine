import React, { useEffect, useRef } from 'react';

// ============================================================================
// TYPESCRIPT INTERFACES
// ============================================================================
/**
 * Props interface for the WelcomeScreen component
 * @param handleSubmit - Function called when user submits a message
 * @param isLoading - Boolean flag indicating if submission is in progress
 * @param onCancel - Function called when user cancels the operation
 */
interface WelcomeScreenProps {
  handleSubmit: (query: string) => void;
  isLoading: boolean;
  onCancel: () => void;
}

// ============================================================================
// IMAGE IMPORTS SECTION
// ============================================================================
/**
 * Import your agent profile images here
 * CUSTOMIZATION: 
 * - Replace these paths with your actual image locations
 * - Supported formats: PNG, JPG, JPEG, GIF, SVG
 * - Recommended size: 300x300px minimum for best quality
 * - Images should be square for circular display
 * 
 * To add a new agent image:
 * 1. Import the image: import newAgentImg from "../../path/to/image.png";
 * 2. Add it to the corresponding agent object below
 */
import NexusImg from "../../agents/ACE_Nexus.png";
import SentinelImg from "../../agents/ACE_Sentinel.png";
import GearsImg from "../../agents/ACE_Gears.png"

import AtlasImg from "../../agents/ACE_Atlas.png";
import MaestroImg from "../../agents/ACE_Maestro.png";
import PulseImg from "../../agents/ACE_Pulse.png";
import AegisImg from "../../agents/ACE_Aegis.png";
import SageImg from "../../agents/ACE_Sage.png";
import LexiImg from "../../agents/ACE_Lexi.png";
import ScoutImg from "../../agents/ACE_Scout.png";

// Logo and decorative images
import logoImg from "../../agents/metro_one_logo.png";
import robotImg from "../../agents/robot_hand.png";

// Commander image
import commanderImg from "../../agents/ACE_Carlos1.png";

// ============================================================================
// AGENT TYPE INTERFACE
// ============================================================================
interface AgentConfig {
  name: string;
  role: string;
  description: string;
  initials: string;
  gradient: string;
  image: string | null;
}

// ============================================================================
// AGENT DATA CONFIGURATION
// ============================================================================
/**
 * Agent configuration object
 * CUSTOMIZATION:
 * - name: Display name for the agent
 * - role: Job title or specialization
 * - description: Brief bio or capabilities (1-2 sentences)
 * - initials: Used for fallback avatar when no image is available
 * - gradient: Background gradient for initials display (CSS gradient string)
 * - image: Imported image variable or null for initials display
 * 
 * To add a new agent:
 * 1. Add a new property to this object
 * 2. Include all required fields
 * 3. Update the TeamMemberCard component usage in the main render
 */
const agents = {
  // ===== CHIEF ORCHESTRATOR =====
  nexus: {
    name: "Nexus",
    role: "Chief AI Agent",
    description: "Routes queries, coordinates agents, synthesizes multi-source intelligence.",
    initials: "NX",
    gradient: "linear-gradient(135deg, #FFA500, #FF6347)", // Orange to red gradient
    image: NexusImg
  },

  // ===== CORE SPECIALIST AGENTS =====
  atlas: {
    name: "Atlas", 
    role: "PERFORMANCE ANALYTICS",
    description: "Analyzes trends, cost drivers and KPI performance..",
    initials: "AT",
    gradient: "linear-gradient(135deg, #00BFFF, #1E90FF)", // Blue gradient
    image: AtlasImg
  },
  maestro: {
    name: "Maestro",
    role: "CAPACITY OPTIMIZATION",
    description: "FTE optimization and capacity balancing.",
    initials: "MA",
    gradient: "linear-gradient(135deg, #32CD32, #228B22)", // Green gradient
    image: MaestroImg
  },
  pulse: {
    name: "Pulse",
    role: "COMMS INTELLIGENCE",
    description: "Tracks email/SMS patterns, flags escalations, monitors response times.",
    initials: "PL",
    gradient: "linear-gradient(135deg, #8A2BE2, #4B0082)", // Violet to indigo
    image: PulseImg
  },
  aegis: {
    name: "Aegis",
    role: "Compliance",
    description: "Monitors certification gaps, tracks mandatory training, ensures audit readiness.",
    initials: "AG",
    gradient: "linear-gradient(135deg, #DA70D6, #FF69B4)", // Purple to pink gradient
    image: AegisImg
  },
  sage: {
    name: "Sage",
    role: "STRATEGIC RESEARCH",
    description: "Delivers competitive intel, industry trends, and executive foresight briefs.",
    initials: "SG",
    gradient: "linear-gradient(135deg, #FFD700, #FF8C00)", // Gold to deep orange
    image: SageImg
  },
  lexi: {
    name: "Lexi",
    role: "KNOWLEDGE BASE",
    description: "Retrieves policies, SOPs, and manuals with source citations via RAG.",
    initials: "LX",
    gradient: "linear-gradient(135deg, #25C6F7, #5468FF)", // cyan → indigo
    image: LexiImg
  },
  scout: {
    name: "Scout",
    role: "MARKET INTELLIGENCE",
    description: "Surfaces demand signals, seasonality patterns, and external market trends.",
    initials: "SC",
    gradient: "linear-gradient(135deg, #14b8a6, #0ea5e9)", // Teal to Sky
    image: ScoutImg
  },

  // ===== SUPPORT CHIEFS (flank the Chief Orchestrator) =====
  gears: {
    name: "Gears",
    role: "Workflow Automation",
    description: "Workflow automation: scheduled tasks and system integrations.",
    initials: "GR",
    gradient: "linear-gradient(135deg, #10b981, #06b6d4)", // Emerald to Cyan
    image: GearsImg // TODO: Add GearsImg when available
  },
  sentinel: {
    name: "Sentinel",
    role: "Real-Time Monitoring",
    description: "Monitoring & alerts: anomalies, thresholds, SLA risk, watchlists.",
    initials: "SN",
    gradient: "linear-gradient(135deg, #f59e0b, #f97316)", // Amber to Orange
    image: SentinelImg
  },
};

// ============================================================================
// TEAM MEMBER CARD COMPONENT
// ============================================================================
/**
 * TeamMemberCard - Individual agent display component with 3D hover effects
 * 
 * @param agent - Agent data object from the agents configuration
 * @param isLeader - Boolean to apply special styling for team leader
 * 
 * CUSTOMIZATION:
 * - Adjust avatar size by modifying width/height (line 127-128)
 * - Change animation delays (line 119-120)
 * - Modify shadow effects (lines 139-143)
 * - Customize text styling (lines 196-220)
 */
const TeamMemberCard = ({ agent, isLeader = false, settings, delay, hideDescription = false }: { 
  agent: AgentConfig; 
  isLeader?: boolean;
  settings: {
    glowIntensity: number;
    animationSpeed: number;
    particleDensity: number;
    brightness: number;
    effectsEnabled: boolean;
  };
  delay?: string;
  hideDescription?: boolean;
}) => {
  // Size configuration based on leader status
  const avatarSize = isLeader ? 175 : 120;
  const nameSize = isLeader ? 35 : 26;
  const roleSize = isLeader ? 16 : 13;
  const descSize = isLeader ? 16 : 14;
  const initialsSize = isLeader ? 40 : 28;

  // Refs for 3D rotation effect
  const cardRef = useRef<HTMLDivElement>(null);
  const avatarRef = useRef<HTMLDivElement>(null);

  // 3D hover effect implementation
  useEffect(() => {
    const card = cardRef.current;
    const avatar = avatarRef.current;
    if (!card || !avatar) return;

    /**
     * Mouse move handler for 3D rotation effect
     * CUSTOMIZATION: Adjust division factors (10) to increase/decrease rotation sensitivity
     */
    const handleMouseMove = (e: MouseEvent) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateY = (x - centerX) / 10; // Adjust divisor for rotation intensity
      const rotateX = -(y - centerY) / 10; // Adjust divisor for rotation intensity
      avatar.style.transform = `perspective(1000px) rotateY(${rotateY}deg) rotateX(${rotateX}deg) scale(1.35)`;
    };

    const handleMouseLeave = () => {
      avatar.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg) scale(1)';
    };

    card.addEventListener('mousemove', handleMouseMove);
    card.addEventListener('mouseleave', handleMouseLeave);
    return () => {
      card.removeEventListener('mousemove', handleMouseMove);
      card.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  return (
    <div ref={cardRef} style={{ 
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      cursor: 'pointer',
      transition: 'transform 0.3s ease',
      animation: 'fadeInUp 0.8s ease-out forwards',
      animationDelay: delay || (isLeader ? '0.3s' : '1.8s'),
      opacity: 0
    }}>
      {/* Avatar Container with 3D effects */}
      <div ref={avatarRef} style={{ 
        position: 'relative',
        width: `${avatarSize}px`,
        height: `${avatarSize}px`,
        marginBottom: '5px',
        transformStyle: 'preserve-3d',
        transition: 'transform 0.6s cubic-bezier(0.175, 0.885, 0.32, 0.275)' // Smooth 3D transition
      }}>
        {/* Online Indicator - Glowing */}
        <div style={{
          position: 'absolute',
          bottom: isLeader ? '8px' : '4px',
          right: isLeader ? '8px' : '4px',
          width: isLeader ? '20px' : '14px',
          height: isLeader ? '20px' : '14px',
          borderRadius: '50%',
          background: '#30d158',
          border: `${isLeader ? '3px' : '2px'} solid rgba(0,0,0,0.8)`,
          boxShadow: '0 0 8px #30d158, 0 0 16px #30d158, 0 0 24px rgba(48, 209, 88, 0.5)',
          zIndex: 20,
          animation: 'glowPulse 2s ease-in-out infinite'
        }} />
        {/* Main avatar circle with metallic effect */}
        <div style={{
          width: '100%',
          height: '100%',
          borderRadius: '50%',
          position: 'relative',
          overflow: 'hidden',
          background: 'linear-gradient(145deg, #1a1a1a, #2a2a2a)', // Dark metallic background
          // Complex shadow for depth effect
          boxShadow: `30px 30px 60px rgba(0, 0, 0, 0.8),
                      -30px -30px 60px rgba(255, 255, 255, 0.02),
                      inset 2px 2px 5px rgba(255, 255, 255, 0.1),
                      inset -2px -2px 5px rgba(0, 0, 0, 0.5),
                      0 0 40px rgba(255, 255, 255, 0.05)`
        }}>
          {/* Metallic ring decoration */}
          <div style={{
            position: 'absolute',
            inset: '-4px',
            borderRadius: '10%',
            background: 'linear-gradient(135deg, rgba(255,255,255,0.3), rgba(192,192,192,0.2), rgba(255,255,255,0.1), rgba(128,128,128,0.2))',
            opacity: 0.7,
            zIndex: -1
          }} />
          
          {/* Avatar content - Image or Initials fallback */}
          {agent.image ? (
            // Display agent image if available
            <img 
              src={agent.image}
              alt={agent.name}
              style={{
                width: '100%',
                height: '100%',
                borderRadius: '50%',
                objectFit: 'cover', // Ensures image fills circle properly
                position: 'relative',
                zIndex: 1
              }}
            />
          ) : (
            // Fallback to initials with gradient background
            <div style={{
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: agent.gradient, // Use agent's custom gradient
              position: 'relative',
              zIndex: 1
            }}>
              <span style={{
                fontSize: `${initialsSize}px`,
                fontWeight: 'bold',
                color: 'rgba(255, 255, 255, 0.9)',
                textShadow: '2px 2px 4px rgba(0,0,0,0.3)'
              }}>{agent.initials}</span>
            </div>
          )}
          
          {/* Glass shine effect for premium look */}
          <div style={{
            position: 'absolute',
            top: '10%',
            left: '10%',
            width: '140%',
            height: '40%',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(255,255,255,0.6), transparent 70%)',
            filter: 'blur(20px)'
          }} />
        </div>
      </div>

      {/* Agent Information Section */}
      <div style={{ textAlign: 'center', maxWidth: isLeader ? '350px' : '200px', minHeight: hideDescription ? '50px' : 'auto' }}>
        {/* Agent Name */}
        <h2 style={{
          fontSize: `${nameSize}px`,
          fontWeight: 750,
          marginBottom: '2px',
          background: 'linear-gradient(90deg, #ffffff, #e0e0e0)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>{agent.name}</h2>
        
        {/* Agent Role */}
        <p style={{
          fontSize: `${roleSize}px`,
          fontWeight: 550,
          color: 'rgba(233, 222, 20, 0.94)',
          marginBottom: '3px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>{agent.role}</p>
        
        {/* Agent Description - Hidden when Org View active */}
        {!hideDescription && (
          <p style={{
            fontSize: `${descSize}px`,
            lineHeight: '1.5',
            color: 'rgba(255, 255, 255, 0.5)',
            fontWeight: 300
          }}>{agent.description}</p>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// MAIN WELCOME SCREEN COMPONENT
// ============================================================================
/**
 * Main welcome screen with team display and chat interface
 * 
 * CUSTOMIZATION GUIDE:
 * 1. Background: Modify gradient (line 241)
 * 2. Decorative elements: Adjust positions and animations (lines 257-326)
 * 3. Title text: Change company/team names (lines 345-370)
 * 4. Team layout: Modify grid arrangement (lines 382-394)
 * 5. Chat section: Customize input styling (lines 401-459)
 */
export function WelcomeScreen({ handleSubmit, isLoading, onCancel }: WelcomeScreenProps) {
  // State for chat message input
  const [message, setMessage] = React.useState('');

 // Settings State
  const [showSettings, setShowSettings] = React.useState(false);
  const [settings, setSettings] = React.useState({
    glowIntensity: 1,
    animationSpeed: 1,
    particleDensity: 4,
    brightness: 1,
    effectsEnabled: true,
  });

  // Reporting Lines State
  const [showReportingLines, setShowReportingLines] = React.useState(false);

  // Handle chat submission
  const handleChatSubmit = () => {
    if (!message.trim()) return;
    handleSubmit(message);
    setMessage(''); // Clear input after submission
  };

  return (
   <div 
     className="min-h-screen w-screen bg-black flex flex-col items-center justify-center relative overflow-hidden p-8 m-0 box-sizing"
     style={{ filter: `brightness(${settings.brightness})`, transition: 'filter 0.3s ease' }}
   >
    
      {/* ===== SETTINGS BUTTON - Upper Right ===== */}
      <button 
        onClick={() => setShowSettings(!showSettings)} 
        style={{
          position: 'fixed',
          top: '160px',
          right: '320px',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '14px 24px',
          background: 'rgba(0,0,0,0.6)',
          backdropFilter: 'blur(40px)',
          border: '1px solid rgba(255,255,255,0.15)',
          borderRadius: '100px',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          animation: 'fadeInDown 1s ease-out 0.5s both'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'rgba(10, 132, 255, 0.5)';
          e.currentTarget.style.transform = 'scale(1.05)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)';
          e.currentTarget.style.transform = 'scale(1)';
        }}
      >
        <svg 
          width="40" 
          height="40" 
          fill="none" 
          stroke="rgba(10, 132, 255, 1)" 
          strokeWidth="2" 
          viewBox="0 0 24 24"
          style={{ transition: 'transform 0.5s ease' }}
          className="settings-icon"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <span style={{ 
          fontSize: '14px', 
          fontWeight: 500, 
          color: 'rgba(255,255,255,0.9)',
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif'
        }}>Settings</span>
      </button>

      {/* ===== ORG VIEW TOGGLE BUTTON - Upper Right ===== */}
      <button 
        onClick={() => setShowReportingLines(!showReportingLines)} 
        style={{
          position: 'fixed',
          top: '160px',
          right: '120px',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '14px 24px',
          background: showReportingLines ? 'rgba(251, 191, 36, 0.2)' : 'rgba(0,0,0,0.6)',
          backdropFilter: 'blur(40px)',
          border: showReportingLines ? '1px solid rgba(251, 191, 36, 0.6)' : '1px solid rgba(255,255,255,0.15)',
          borderRadius: '100px',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          animation: 'fadeInDown 1s ease-out 0.6s both'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = 'rgba(251, 191, 36, 0.8)';
          e.currentTarget.style.transform = 'scale(1.05)';
          e.currentTarget.style.boxShadow = '0 0 20px rgba(251, 191, 36, 0.3)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = showReportingLines ? 'rgba(251, 191, 36, 0.6)' : 'rgba(255,255,255,0.15)';
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        <svg 
          width="40" 
          height="40" 
          fill="none" 
          stroke={showReportingLines ? 'rgba(251, 191, 36, 1)' : 'rgba(255,255,255,0.7)'} 
          strokeWidth="2" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
        </svg>
        <span style={{ 
          fontSize: '14px', 
          fontWeight: 500, 
          color: showReportingLines ? 'rgba(251, 191, 36, 1)' : 'rgba(255,255,255,0.9)',
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif'
        }}>Org View</span>
      </button>

      {/* ===== SETTINGS PANEL - Slides from Left ===== */}
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        height: '100%',
        width: '380px',
        background: 'rgba(0,0,0,0.95)',
        backdropFilter: 'blur(40px)',
        borderRight: '1px solid rgba(255,255,255,0.1)',
        boxShadow: '20px 0 60px rgba(0,0,0,0.5)',
        transform: showSettings ? 'translateX(0)' : 'translateX(-100%)',
        transition: 'transform 0.3s ease',
        zIndex: 150,
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Panel Header */}
        <div style={{
          padding: '24px',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          background: 'linear-gradient(135deg, rgba(99,102,241,0.1), rgba(59,130,246,0.1), rgba(34,211,238,0.1))'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #6366f1, #3b82f6, #22d3ee)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <svg width="20" height="20" fill="none" stroke="#fff" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#fff', margin: 0 }}>Settings</h2>
            </div>
            <button
              onClick={() => setShowSettings(false)}
              style={{
                padding: '8px',
                background: 'transparent',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'background 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
            >
              <svg width="20" height="20" fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '8px' }}>Customize your Nexus Command experience</p>
        </div>

        {/* Settings Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* ✨ Glow Intensity */}
          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '12px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#3b82f6', animation: 'glowPulse 2s ease-in-out infinite' }} />
              Glow Intensity: {Math.round(settings.glowIntensity * 100)}%
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={settings.glowIntensity}
              onChange={(e) => setSettings({ ...settings, glowIntensity: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: '#3b82f6', height: '6px', borderRadius: '3px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>
              <span>Off</span>
              <span>Normal</span>
              <span>Intense</span>
            </div>
          </div>

          {/* ⚡ Animation Speed */}
          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '12px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#22d3ee', animation: 'glowPulse 2s ease-in-out infinite' }} />
              Animation Speed: {settings.animationSpeed}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={settings.animationSpeed}
              onChange={(e) => setSettings({ ...settings, animationSpeed: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: '#22d3ee', height: '6px', borderRadius: '3px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>
              <span>Slow</span>
              <span>Normal</span>
              <span>Fast</span>
            </div>
          </div>

          {/* 💫 Particle Density */}
          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '12px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#a855f7', animation: 'glowPulse 2s ease-in-out infinite' }} />
              Particle Density: {settings.particleDensity}
            </label>
            <input
              type="range"
              min="0"
              max="8"
              step="1"
              value={settings.particleDensity}
              onChange={(e) => setSettings({ ...settings, particleDensity: parseInt(e.target.value) })}
              style={{ width: '100%', accentColor: '#a855f7', height: '6px', borderRadius: '3px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>
              <span>None</span>
              <span>Some</span>
              <span>Many</span>
            </div>
          </div>

          {/* 💡 Brightness */}
          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '12px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fbbf24', animation: 'glowPulse 2s ease-in-out infinite' }} />
              Brightness: {Math.round(settings.brightness * 100)}%
            </label>
            <input
              type="range"
              min="0.5"
              max="1.5"
              step="0.1"
              value={settings.brightness}
              onChange={(e) => setSettings({ ...settings, brightness: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: '#fbbf24', height: '6px', borderRadius: '3px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>
              <span>Dim</span>
              <span>Normal</span>
              <span>Bright</span>
            </div>
          </div>

          {/* 🎭 Effects Toggle */}
          <div
            onClick={() => setSettings({ ...settings, effectsEnabled: !settings.effectsEnabled })}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '16px',
              background: 'rgba(255,255,255,0.05)',
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.1)',
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '24px' }}>🎭</span>
              <div>
                <p style={{ fontSize: '14px', fontWeight: 600, color: '#fff', margin: 0 }}>Enable Effects</p>
                <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', margin: 0 }}>Animations, glows & particles</p>
              </div>
            </div>
            <div style={{
              width: '48px',
              height: '26px',
              borderRadius: '13px',
              background: settings.effectsEnabled ? '#3b82f6' : 'rgba(255,255,255,0.2)',
              transition: 'background 0.2s',
              position: 'relative'
            }}>
              <div style={{
                width: '22px',
                height: '22px',
                borderRadius: '50%',
                background: '#fff',
                boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                position: 'absolute',
                top: '2px',
                left: settings.effectsEnabled ? '24px' : '2px',
                transition: 'left 0.2s'
              }} />
            </div>
          </div>

          {/* Divider */}
          <div style={{ height: '1px', background: 'rgba(255,255,255,0.1)' }} />

          {/* Reset Button */}
          <button
            onClick={() => setSettings({
              glowIntensity: 1,
              animationSpeed: 1,
              particleDensity: 4,
              brightness: 1,
              effectsEnabled: true,
            })}
            style={{
              width: '100%',
              padding: '14px',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '12px',
              color: '#f87171',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}
          >
            <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Reset to Defaults
          </button>
        </div>

        {/* Panel Footer */}
        <div style={{
          padding: '16px',
          borderTop: '1px solid rgba(255,255,255,0.1)',
          background: 'rgba(0,0,0,0.5)',
          textAlign: 'center'
        }}>
          <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', margin: 0 }}>Nexus Command v1.0</p>
        </div>
      </div>

      {/* Overlay when settings open */}
      {showSettings && (
        <div 
          onClick={() => setShowSettings(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.3)',
            zIndex: 140
          }}
        />
      )}

      {/* ===== CYBER NEON BACKGROUND EFFECTS ===== */}
      {/* Animated grid background - respects effectsEnabled */}
      {settings.effectsEnabled && (
        <div style={{
          position: 'fixed',
          inset: 0,
          opacity: 0.15 * settings.glowIntensity,
          backgroundImage: `
            linear-gradient(rgba(139, 92, 246, 0.15) 1px, transparent 1px),
            linear-gradient(90deg, rgba(139, 92, 246, 0.15) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
          animation: `gridScroll ${25 / settings.animationSpeed}s linear infinite`,
          pointerEvents: 'none'
        }} />
      )}

      {/* Gradient orb - top left - Purple/Pink */}
      {settings.effectsEnabled && settings.particleDensity >= 1 && (
        <div style={{
          position: 'fixed',
          top: '0',
          left: '25%',
          width: '600px',
          height: '600px',
          background: `rgba(168, 85, 247, ${0.20 * settings.glowIntensity})`,
          borderRadius: '50%',
          filter: 'blur(150px)',
          animation: `pulse ${4 / settings.animationSpeed}s ease-in-out infinite`,
          pointerEvents: 'none'
        }} />
      )}

      {/* Gradient orb - bottom right - Pink */}
      {settings.effectsEnabled && settings.particleDensity >= 2 && (
        <div style={{
          position: 'fixed',
          bottom: '0',
          right: '25%',
          width: '500px',
          height: '500px',
          background: `rgba(236, 72, 153, ${0.15 * settings.glowIntensity})`,
          borderRadius: '50%',
          filter: 'blur(120px)',
          animation: `pulse ${4 / settings.animationSpeed}s ease-in-out infinite`,
          animationDelay: '1s',
          pointerEvents: 'none'
        }} />
      )}

      {/* Gradient orb - left side - Cyan */}
      {settings.effectsEnabled && settings.particleDensity >= 3 && (
        <div style={{
          position: 'fixed',
          top: '50%',
          left: '0',
          width: '400px',
          height: '400px',
          background: `rgba(34, 211, 238, ${0.10 * settings.glowIntensity})`,
          borderRadius: '50%',
          filter: 'blur(100px)',
          animation: `pulse ${4 / settings.animationSpeed}s ease-in-out infinite`,
          animationDelay: '2s',
          pointerEvents: 'none'
        }} />
      )}

      {/* Gradient orb - right side - Emerald */}
      {settings.effectsEnabled && settings.particleDensity >= 4 && (
        <div style={{
          position: 'fixed',
          top: '33%',
          right: '0',
          width: '350px',
          height: '350px',
          background: `rgba(16, 185, 129, ${0.10 * settings.glowIntensity})`,
          borderRadius: '50%',
          filter: 'blur(80px)',
          animation: `pulse ${4 / settings.animationSpeed}s ease-in-out infinite`,
          animationDelay: '1.5s',
          pointerEvents: 'none'
        }} />
      )}

      {/* ===== MAIN CONTENT SECTION ===== */}
      <div style={{
        position: 'relative',
        zIndex: 10,
        width: '95%',
        maxWidth: '2200px',
        textAlign: 'center',
        margin: '0 auto'
      }}>
        {/* ===== COMMANDER BADGE - TOP LEFT ===== */}
        <div style={{
          position: 'fixed',
          top: '100px',
          left: '200px',
          display: 'flex',
          alignItems: 'center',
          gap: '20px',
          padding: '16px 28px 16px 16px',
          borderRadius: '100px',
          background: 'rgba(0,0,0,0.6)',
          backdropFilter: 'blur(40px)',
          border: '1px solid rgba(255, 255, 255, 0.52)',
          boxShadow: '0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(10, 132, 255, 0.15)',
          zIndex: 100,
          animation: 'fadeInDown 1s ease-out 0.5s both'
        }}>
          {/* Commander Avatar with Glow Ring */}
          <div style={{ position: 'relative' }}>
            {/* Glow ring - respects settings */}
            {settings.effectsEnabled && (
              <div style={{
                position: 'absolute',
                inset: '-4px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #0a84ff, #5e5ce6, #bf5af2)',
                opacity: 0.8 * settings.glowIntensity,
                filter: `blur(${8 * settings.glowIntensity}px)`,
                animation: `pulse ${3 / settings.animationSpeed}s ease-in-out infinite`
              }} />
            )}
            <div style={{
              position: 'relative',
              width: '180px',
              height: '180px',
              borderRadius: '50%',
              overflow: 'hidden',
              border: '3px solid rgba(255,255,255,0.2)',
              boxShadow: '0 0 30px rgba(10, 132, 255, 0.4)'
            }}>
              <img src={commanderImg} alt="Commander" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
            {/* Online Indicator */}
            <div style={{
              position: 'absolute',
              bottom: '2px',
              right: '2px',
              width: '16px',
              height: '16px',
              borderRadius: '50%',
              background: '#30d158',
              border: '3px solid rgba(0,0,0,0.8)',
              boxShadow: '0 0 12px #30d158'
            }} />
          </div>
          {/* Commander Info */}
          <div style={{ textAlign: 'left' }}>
            <p style={{ 
              fontSize: '15px', 
              fontWeight: 500, 
              color: 'rgba(255,255,255,0.5)',
              lineHeight: 1.2,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              marginBottom: '4px',
              fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif'
            }}>AI Strategy</p>
            <p style={{ 
              fontSize: '27px', 
              fontWeight: 700, 
              color: '#fff',
              lineHeight: 1.1,
              fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif'
            }}>Carlos Guzman</p>
          </div>
        </div>

        {/* Hero Header - Apple Cinematic Style */}
        <header style={{ textAlign: 'center', marginBottom: '50px' }}>
          <h1 style={{
            fontSize: '94px',
            marginTop: '0',
            fontWeight: 700,
            letterSpacing: '-0.05em',
            lineHeight: 1.30,
            marginBottom: '24px',
            background: 'linear-gradient(180deg, #ffffff 0%, rgba(255,255,255,0.5) 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            Agentic Cognitive Enterprise 
          </h1>
          
          <p style={{
            fontSize: '28px',
            fontWeight: 500,
            color: 'rgba(255,255,255,0.8)',
            marginBottom: '12px',
            letterSpacing: '-0.01em'
          }}>Multi-Agent Intelligence Platform</p>
          
          <p style={{
            fontSize: '21px',
            fontWeight: 400,
            color: 'rgba(255,255,255,0.4)',
            letterSpacing: '-0.01em'
          }}>Think different. Think together.</p>
        </header>

        {/* ===== TEAM LAYOUT SECTION - HIERARCHICAL ===== */}

        <div style={{ marginBottom: '50px', marginTop: '30px' }}>
          
          {/* ===== TIER 1: LEADERSHIP ROW (Gears - Nexus - Sentinel) ===== */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'flex-start',
            gap: '60px',
            marginBottom: '20px',
            position: 'relative',
            minHeight: '320px'
          }}>
            {/* Left Support Chief - Gears */}
            <div style={{ transform: 'scale(1)', width: '220px', flexShrink: 0, alignSelf: 'flex-start', paddingTop: '55px' }}>
              <TeamMemberCard agent={agents.gears} settings={settings} delay="0.8s" hideDescription={showReportingLines} />
            </div>

            {/* Center Chief - Nexus */}
            <div style={{ transform: 'scale(1.1)', zIndex: 10, width: '280px', flexShrink: 0, alignSelf: 'flex-start' }}>
              <TeamMemberCard agent={agents.nexus} isLeader={true} settings={settings} delay="0.3s" hideDescription={showReportingLines} />
            </div>

            {/* Right Support Chief - Sentinel */}
            <div style={{ transform: 'scale(1)', width: '220px', flexShrink: 0, alignSelf: 'flex-start', paddingTop: '55px' }}>
              <TeamMemberCard agent={agents.sentinel} settings={settings} delay="1.0s" hideDescription={showReportingLines} />
            </div>
          </div>

          {/* ===== TIER DIVIDER - Hidden when Org View active ===== */}
          {!showReportingLines && (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '16px', 
              maxWidth: '1900px', 
              margin: '0 auto 30px auto',
              padding: '0 20px'
            }}>
              <div style={{ flex: 1, height: '2px', background: 'linear-gradient(90deg, transparent, rgba(168, 85, 247, 0.4), transparent)' }} />
              <span style={{ 
                color: 'rgba(168, 85, 247, 0.7)', 
                fontSize: '24px', 
                fontWeight: 600, 
                letterSpacing: '0.6em'
              }}>CORE AGENTS</span>
              <div style={{ flex: 1, height: '2px', background: 'linear-gradient(90deg, transparent, rgba(168, 85, 247, 0.4), transparent)' }} />
            </div>
          )}

          
          {/* ===== GOLDEN REPORTING LINES ===== */}
          {showReportingLines && (
            <svg 
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
                zIndex: 5
              }}
            >
              <defs>
                <linearGradient id="goldenGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#06b6d4" />
                  <stop offset="50%" stopColor="#22d3ee" />
                  <stop offset="100%" stopColor="#06b6d4" />
                </linearGradient>
                <filter id="goldenGlow" x="-100%" y="-100%" width="300%" height="300%">
                  <feGaussianBlur stdDeviation="3" result="blur1"/>
                  <feGaussianBlur stdDeviation="6" result="blur2"/>
                  <feMerge>
                    <feMergeNode in="blur2"/>
                    <feMergeNode in="blur1"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>

              {/* Single horizontal line: Gears - Nexus - Sentinel */}
              <rect 
                x="38.5%" 
                y="360px" 
                width="23%" 
                height="2.5px"
                fill="#ffffff"
                rx="2"
                filter="url(#goldenGlow)"
              />

              {/* === TOP NODES (on horizontal line) === */}
              <circle cx="38.5%" cy="360px" r="7" fill="#fbbf24" filter="url(#goldenGlow)" />
              <circle cx="50%" cy="360px" r="6" fill="#fbbf24" filter="url(#goldenGlow)" />
              <circle cx="61.5%" cy="360px" r="7" fill="#fbbf24" filter="url(#goldenGlow)" />

              {/* === VERTICAL LINE FROM GEARS === */}
              <rect 
                x="35%" 
                y="540px" 
                width="1.5px" 
                height="125px"
                fill="#ffffff"
                style={{ transform: 'translateX(-1px)' }}
                filter="url(#goldenGlow)"
              />
              <circle cx="35%" cy="540px" r="7" fill="#fbbf24" filter="url(#goldenGlow)" />

              {/* === VERTICAL LINE FROM NEXUS === */}
              <rect 
                x="50%" 
                y="575px" 
                width="1.5px" 
                height="90px"
                fill="#ffffff"
                style={{ transform: 'translateX(-1px)' }}
                filter="url(#goldenGlow)"
              />
              <circle cx="50%" cy="575px" r="7" fill="#fbbf24" filter="url(#goldenGlow)" />

              {/* === VERTICAL LINE FROM SENTINEL === */}
              <rect 
                x="66%" 
                y="540px" 
                width="1.5px" 
                height="125px"
                fill="#ffffff"
                style={{ transform: 'translateX(-1px)' }}
                filter="url(#goldenGlow)"
              />
              <circle cx="66%" cy="540px" r="7" fill="#fbbf24" filter="url(#goldenGlow)" />

              {/* === HORIZONTAL LINE ACROSS CORE AGENTS === */}
              <rect 
                x="9.5%" 
                y="664px" 
                width="81.5%" 
                height="2px"
                fill="#ffffff"
                rx="2"
                filter="url(#goldenGlow)"
              />

              {/* === CORE AGENT NODES (7 agents) === */}
              <circle cx="9.5%" cy="665px" r="6" fill="#fbbf24" filter="url(#goldenGlow)" />
              <circle cx="91%" cy="665px" r="6" fill="#fbbf24" filter="url(#goldenGlow)" />
            </svg>
          )}

         {/* ===== TIER 2: CORE AGENTS GRID ===== */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(7, 1fr)',
            gap: '60px',
            maxWidth: '1900px',
            margin: '0 auto',
            padding: '100px 20px  40px'
          }}>
            <TeamMemberCard agent={agents.atlas} settings={settings} hideDescription={showReportingLines} />
            <TeamMemberCard agent={agents.maestro} settings={settings} hideDescription={showReportingLines} />
            <TeamMemberCard agent={agents.pulse} settings={settings} hideDescription={showReportingLines} />
            <TeamMemberCard agent={agents.aegis} settings={settings} hideDescription={showReportingLines} />
            <TeamMemberCard agent={agents.sage} settings={settings} hideDescription={showReportingLines} />
            <TeamMemberCard agent={agents.lexi} settings={settings} hideDescription={showReportingLines} />
            <TeamMemberCard agent={agents.scout} settings={settings} hideDescription={showReportingLines} />
          </div>
        </div>

       {/* ===== CHAT INTERFACE SECTION - APPLE CLEAN LINE STYLE ===== */}
        <div style={{ 
          maxWidth: '1500px', 
          margin: '0 auto',
          animation: 'fadeInUp 1s ease-out 1s both'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '18px',
            borderBottom: '1px solid rgba(236, 230, 230, 0.89)',
            paddingBottom: '10px'

          }}>
            <input 
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="All agents standing by..."
              style={{
                flex: 1,
                padding: '0',
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: '#f0f1ebfa',
                fontSize: '32px',
                fontWeight: 400,
                fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif'
              }}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleChatSubmit();
                }
              }}
            />
            <button
              onClick={handleChatSubmit}
              disabled={isLoading || !message.trim()}
              style={{
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                background: isLoading || !message.trim() ? 'rgba(20, 49, 235, 0.87)' : '#0a84ff',
                border: 'none',
                cursor: isLoading || !message.trim() ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s ease',
                flexShrink: 0
              }}
            >
              <svg width="20" height="20" fill="none" stroke="#fff" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </button>
          </div>
          <p style={{
            fontSize: '13px',
            color: 'rgba(255, 255, 255, 0.85)',
            marginTop: '12px',
            textAlign: 'center',
            fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif'
          }}>Welcome to the Future</p>
        </div>
      </div>

       {/* ===== CYBER NEON CSS ANIMATIONS ===== */}
      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }
        
        body {
          margin: 0;
          padding: 0;
          overflow-x: hidden;
        }
        
        /* Animated grid scroll */
        @keyframes gridScroll {
          0% { transform: translate(0, 0); }
          100% { transform: translate(60px, 60px); }
        }

        /* Pulse animation for gradient orbs */
        @keyframes pulse {
          0%, 100% { opacity: 0.6; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.05); }
        }

        /* Floating animation for decorative elements */
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-20px); }
        }

        /* Shimmer effect for neon text */
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }

        /* Fade in from bottom animation */
        @keyframes fadeInUp {
          from { 
            opacity: 0; 
            transform: translateY(30px);
          }
          to { 
            opacity: 1; 
            transform: translateY(0); 
          }
        }

        /* Fade in from top animation */
        @keyframes fadeInDown {
          from { 
            opacity: 0; 
            transform: translateY(-30px);
          }
          to { 
            opacity: 1; 
            transform: translateY(0); 
          }
        }

        /* Neon glow pulse for avatars */
        @keyframes pulseGlow {
          0%, 100% { 
            filter: drop-shadow(0 0 10px rgba(168, 85, 247, 0.4));
          }
          50% { 
            filter: drop-shadow(0 0 30px rgba(236, 72, 153, 0.8)) drop-shadow(0 0 60px rgba(168, 85, 247, 0.5));
          }
        }

        /* Neon border animation */
        @keyframes neonBorder {
          0%, 100% { 
            box-shadow: 0 0 5px rgba(236, 72, 153, 0.5), 0 0 20px rgba(168, 85, 247, 0.3);
          }
          50% { 
            box-shadow: 0 0 10px rgba(236, 72, 153, 0.8), 0 0 40px rgba(168, 85, 247, 0.5), 0 0 60px rgba(34, 211, 238, 0.3);
          }
        }

        /* Rotating ring animation */
        @keyframes spinSlow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        /* Gradient shift animation */
        @keyframes gradientShift {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }

        /* Glowing pulse for online indicators */
        @keyframes glowPulse {
          0%, 100% { 
            box-shadow: 0 0 8px #30d158, 0 0 16px #30d158, 0 0 24px rgba(48, 209, 88, 0.5);
          }
          50% { 
            box-shadow: 0 0 12px #30d158, 0 0 24px #30d158, 0 0 36px rgba(48, 209, 88, 0.8);
          }
        }

        /* Settings icon rotation on hover */
        button:hover .settings-icon {
          transform: rotate(180deg);
        }

        /* Pulsing nodes animation */
        .pulse-node {
          animation: nodePulse 2s ease-in-out infinite;
        }

        @keyframes nodePulse {
          0%, 100% { 
            opacity: 0.9;
          }
          50% { 
            opacity: 1;
          }
        }

        /* Pulsing nodes animation */
        .pulse-node {
          animation: nodePulse 2s ease-in-out infinite;
        }

        @keyframes nodePulse {
          0%, 100% { 
            opacity: 0.9;
          }
          50% { 
            opacity: 1;
          }
        }

        /* ===== GOLDEN REPORTING LINES ANIMATIONS ===== */
        .golden-line {
          stroke-dasharray: 1000;
          stroke-dashoffset: 1000;
          animation: drawGoldenLine 1.2s ease-out forwards;
        }
        
        .line-1 { animation-delay: 0.1s; }
        .line-2 { animation-delay: 0.2s; }
        .line-3 { animation-delay: 0.4s; }
        .line-4 { animation-delay: 0.6s; }
        .line-5 { animation-delay: 0.8s; }
        .line-6 { animation-delay: 0.9s; }
        .line-7 { animation-delay: 1.0s; }
        .line-8 { animation-delay: 1.1s; }

        .golden-node {
          opacity: 0;
          transform-origin: center;
          animation: nodeAppear 0.5s ease-out forwards, nodePulse 2s ease-in-out infinite;
        }

        .node-1 { animation-delay: 0s, 0.5s; }
        .node-2 { animation-delay: 0.3s, 0.8s; }
        .node-3 { animation-delay: 0.5s, 1s; }
        .node-4 { animation-delay: 0.7s, 1.2s; }
        .node-5 { animation-delay: 0.9s, 1.4s; }
        .node-6 { animation-delay: 1.1s, 1.6s; }
        .node-7 { animation-delay: 1.3s, 1.8s; }

        @keyframes drawGoldenLine {
          to {
            stroke-dashoffset: 0;
          }
        }

        @keyframes nodeAppear {
          from {
            opacity: 0;
            transform: scale(0);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        @keyframes nodePulse {
          0%, 100% {
            filter: url(#nodeGlow) brightness(1);
            transform: scale(1);
          }
          50% {
            filter: url(#nodeGlow) brightness(1.3);
            transform: scale(1.2);
          }
        }
      `}</style>
    </div>
  );
}