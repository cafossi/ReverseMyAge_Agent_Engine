import React, { useEffect, useRef } from 'react';

// ============================================================================
// TYPESCRIPT INTERFACES
// ============================================================================
interface WelcomeScreenProps {
  handleSubmit: (query: string) => void;
  isLoading: boolean;
  onCancel: () => void;
}

// ============================================================================
// IMAGE IMPORTS SECTION
// ============================================================================
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

import logoImg from "../../agents/metro_one_logo.png";
import robotImg from "../../agents/robot_hand.png";
import commanderImg from "../../agents/ACE_Carlos.png";

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
const agents = {
  nexus: {
    name: "Nexus",
    role: "Chief AI Agent",
    description: "Routes queries, coordinates agents, synthesizes multi-source intelligence.",
    initials: "NX",
    gradient: "linear-gradient(135deg, #00d4ff, #0099cc)",
    image: NexusImg
  },
  atlas: {
    name: "Atlas", 
    role: "Performance Analytics",
    description: "Analyzes trends, cost drivers and KPI performance.",
    initials: "AT",
    gradient: "linear-gradient(135deg, #00d4ff, #0066aa)",
    image: AtlasImg
  },
  maestro: {
    name: "Maestro",
    role: "Capacity Optimization",
    description: "FTE optimization and capacity balancing.",
    initials: "MA",
    gradient: "linear-gradient(135deg, #2ed573, #1e8449)",
    image: MaestroImg
  },
  pulse: {
    name: "Pulse",
    role: "Comms Intelligence",
    description: "Tracks email/SMS patterns, flags escalations, monitors response times.",
    initials: "PL",
    gradient: "linear-gradient(135deg, #a55eea, #8854d0)",
    image: PulseImg
  },
  aegis: {
    name: "Aegis",
    role: "Compliance",
    description: "Monitors certification gaps, tracks mandatory training, ensures audit readiness.",
    initials: "AG",
    gradient: "linear-gradient(135deg, #ff4757, #c0392b)",
    image: AegisImg
  },
  sage: {
    name: "Sage",
    role: "Strategic Research",
    description: "Delivers competitive intel, industry trends, and executive foresight briefs.",
    initials: "SG",
    gradient: "linear-gradient(135deg, #ffa502, #cc8400)",
    image: SageImg
  },
  lexi: {
    name: "Lexi",
    role: "Knowledge Base",
    description: "Retrieves policies, SOPs, and manuals with source citations via RAG.",
    initials: "LX",
    gradient: "linear-gradient(135deg, #00d4ff, #5468ff)",
    image: LexiImg
  },
  scout: {
    name: "Scout",
    role: "Market Intelligence",
    description: "Surfaces demand signals, seasonality patterns, and external market trends.",
    initials: "SC",
    gradient: "linear-gradient(135deg, #00cec9, #0984e3)",
    image: ScoutImg
  },
  gears: {
    name: "Gears",
    role: "Workflow Automation",
    description: "Workflow automation: scheduled tasks and system integrations.",
    initials: "GR",
    gradient: "linear-gradient(135deg, #2ed573, #00cec9)",
    image: GearsImg
  },
  sentinel: {
    name: "Sentinel",
    role: "Real-Time Monitoring",
    description: "Monitoring & alerts: anomalies, thresholds, SLA risk, watchlists.",
    initials: "SN",
    gradient: "linear-gradient(135deg, #ffa502, #ff6348)",
    image: SentinelImg
  },
};

// ============================================================================
// TEAM MEMBER CARD COMPONENT - TECH THEME
// ============================================================================
const TeamMemberCard = ({ 
  agent, 
  isLeader = false, 
  settings, 
  delay, 
  hideDescription = false 
}: { 
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
  const avatarSize = isLeader ? 180 : 120;
  const nameSize = isLeader ? 32 : 22;
  const roleSize = isLeader ? 14 : 11;
  const descSize = isLeader ? 14 : 12;
  const initialsSize = isLeader ? 48 : 32;

  const cardRef = useRef<HTMLDivElement>(null);
  const avatarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const card = cardRef.current;
    const avatar = avatarRef.current;
    if (!card || !avatar) return;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateY = (x - centerX) / 12;
      const rotateX = -(y - centerY) / 12;
      avatar.style.transform = `perspective(1000px) rotateY(${rotateY}deg) rotateX(${rotateX}deg) scale(1.08)`;
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
    <div 
      ref={cardRef} 
      style={{ 
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        cursor: 'pointer',
        transition: 'all 0.3s ease',
        animation: 'fadeInUp 0.8s ease-out forwards',
        animationDelay: delay || (isLeader ? '0.3s' : '1.2s'),
        opacity: 0,
        padding: '20px',
        borderRadius: '8px',
        background: 'rgba(0, 212, 255, 0.03)',
        border: '1px solid rgba(0, 212, 255, 0.12)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-8px)';
        e.currentTarget.style.borderColor = 'rgba(0, 212, 255, 0.4)';
        e.currentTarget.style.boxShadow = '0 0 40px rgba(0, 212, 255, 0.15), 0 20px 40px rgba(0, 0, 0, 0.3)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.borderColor = 'rgba(0, 212, 255, 0.12)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      {/* Avatar Container */}
      <div 
        ref={avatarRef} 
        style={{ 
          position: 'relative',
          width: `${avatarSize}px`,
          height: `${avatarSize}px`,
          marginBottom: '16px',
          transformStyle: 'preserve-3d',
          transition: 'transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 0.275)'
        }}
      >
        {/* Cyan Glow Ring */}
        {settings.effectsEnabled && (
          <div style={{
            position: 'absolute',
            inset: '-4px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, rgba(0, 212, 255, 0.6), rgba(0, 153, 204, 0.3))',
            opacity: 0.5 * settings.glowIntensity,
            filter: `blur(${10 * settings.glowIntensity}px)`,
            animation: `techPulse ${3 / settings.animationSpeed}s ease-in-out infinite`
          }} />
        )}
        
        {/* Online Indicator */}
        <div style={{
          position: 'absolute',
          bottom: isLeader ? '10px' : '6px',
          right: isLeader ? '10px' : '6px',
          width: isLeader ? '18px' : '12px',
          height: isLeader ? '18px' : '12px',
          borderRadius: '50%',
          background: '#2ed573',
          border: `2px solid #0a0f1a`,
          boxShadow: '0 0 10px rgba(46, 213, 115, 0.6), 0 0 20px rgba(46, 213, 115, 0.4)',
          zIndex: 20,
          animation: 'statusPulse 2s ease-in-out infinite'
        }} />
        
        {/* Main Avatar Circle */}
        <div style={{
          width: '100%',
          height: '100%',
          borderRadius: '50%',
          position: 'relative',
          overflow: 'hidden',
          background: '#0a0f1a',
          border: '2px solid rgba(0, 212, 255, 0.3)',
          boxShadow: `
            0 0 30px rgba(0, 212, 255, 0.2),
            inset 0 0 20px rgba(0, 0, 0, 0.5)
          `
        }}>
          {/* Circuit Line Decoration */}
          <div style={{
            position: 'absolute',
            top: '0',
            left: '50%',
            transform: 'translateX(-50%)',
            width: '60%',
            height: '2px',
            background: 'linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.5), transparent)',
            boxShadow: '0 0 10px rgba(0, 212, 255, 0.4)'
          }} />
          
          {agent.image ? (
            <img 
              src={agent.image}
              alt={agent.name}
              style={{
                width: '100%',
                height: '100%',
                borderRadius: '50%',
                objectFit: 'cover',
                position: 'relative',
                zIndex: 1
              }}
            />
          ) : (
            <div style={{
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: agent.gradient,
              position: 'relative',
              zIndex: 1
            }}>
              <span style={{
                fontFamily: "'Orbitron', 'Inter', sans-serif",
                fontSize: `${initialsSize}px`,
                fontWeight: 800,
                color: '#0a0f1a',
                textShadow: '0 2px 4px rgba(0,0,0,0.2)'
              }}>{agent.initials}</span>
            </div>
          )}
        </div>
      </div>

      {/* Agent Information */}
      <div style={{ textAlign: 'center', maxWidth: isLeader ? '320px' : '180px', minHeight: hideDescription ? '50px' : 'auto' }}>
        {/* Agent Name */}
        <h2 style={{
          fontFamily: "'Orbitron', 'Inter', sans-serif",
          fontSize: `${nameSize}px`,
          fontWeight: 800,
          marginBottom: '6px',
          color: '#ffffff',
          textShadow: `
            0 0 10px rgba(255, 255, 255, 0.5),
            0 0 30px rgba(0, 212, 255, 0.4)
          `,
          letterSpacing: '1px'
        }}>{agent.name}</h2>
        
        {/* Agent Role */}
        <p style={{
          fontSize: `${roleSize}px`,
          fontWeight: 600,
          color: '#00d4ff',
          marginBottom: '8px',
          textTransform: 'uppercase',
          letterSpacing: '2px',
          textShadow: '0 0 10px rgba(0, 212, 255, 0.4)'
        }}>{agent.role}</p>
        
        {/* Agent Description */}
        {!hideDescription && (
          <p style={{
            fontSize: `${descSize}px`,
            lineHeight: '1.6',
            color: 'rgba(255, 255, 255, 0.6)',
            fontWeight: 400
          }}>{agent.description}</p>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// MAIN WELCOME SCREEN COMPONENT - TECH THEME
// ============================================================================
export function WelcomeScreen({ handleSubmit, isLoading, onCancel }: WelcomeScreenProps) {
  const [message, setMessage] = React.useState('');
  const [showSettings, setShowSettings] = React.useState(false);
  const [settings, setSettings] = React.useState({
    glowIntensity: 1,
    animationSpeed: 1,
    particleDensity: 4,
    brightness: 1,
    effectsEnabled: true,
  });
  const [showReportingLines, setShowReportingLines] = React.useState(false);

  const handleChatSubmit = () => {
    if (!message.trim()) return;
    handleSubmit(message);
    setMessage('');
  };

  return (
    <div 
      className="min-h-screen w-screen flex flex-col items-center justify-center relative overflow-hidden p-8 m-0"
      style={{ 
        background: '#0a0f1a',
        filter: `brightness(${settings.brightness})`, 
        transition: 'filter 0.3s ease',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
      }}
    >
      {/* ===== BACKGROUND EFFECTS ===== */}
      {/* Radial gradient overlays */}
      {settings.effectsEnabled && (
        <>
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: `
              radial-gradient(circle at 20% 80%, rgba(0, 212, 255, ${0.08 * settings.glowIntensity}) 0%, transparent 50%),
              radial-gradient(circle at 80% 20%, rgba(0, 212, 255, ${0.06 * settings.glowIntensity}) 0%, transparent 50%),
              radial-gradient(circle at 50% 50%, rgba(0, 212, 255, ${0.03 * settings.glowIntensity}) 0%, transparent 70%)
            `,
            pointerEvents: 'none',
            zIndex: 0
          }} />
          
          {/* Subtle grid pattern */}
          {settings.particleDensity >= 2 && (
            <div style={{
              position: 'fixed',
              inset: 0,
              opacity: 0.05 * settings.glowIntensity,
              backgroundImage: `
                linear-gradient(rgba(0, 212, 255, 0.3) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 212, 255, 0.3) 1px, transparent 1px)
              `,
              backgroundSize: '80px 80px',
              animation: `gridScroll ${30 / settings.animationSpeed}s linear infinite`,
              pointerEvents: 'none'
            }} />
          )}
        </>
      )}

      {/* ===== SETTINGS BUTTON ===== */}
      <button 
        onClick={() => setShowSettings(!showSettings)} 
        style={{
          position: 'fixed',
          top: '32px',
          left: '32px',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '14px 24px',
          background: 'rgba(0, 212, 255, 0.05)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(0, 212, 255, 0.3)',
          borderRadius: '4px',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          animation: 'fadeInDown 1s ease-out 0.5s both'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = '#00d4ff';
          e.currentTarget.style.boxShadow = '0 0 20px rgba(0, 212, 255, 0.3)';
          e.currentTarget.style.background = 'rgba(0, 212, 255, 0.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = 'rgba(0, 212, 255, 0.3)';
          e.currentTarget.style.boxShadow = 'none';
          e.currentTarget.style.background = 'rgba(0, 212, 255, 0.05)';
        }}
      >
        <svg 
          width="18" 
          height="18" 
          fill="none" 
          stroke="#00d4ff" 
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
          fontWeight: 600, 
          color: '#ffffff',
          letterSpacing: '0.5px'
        }}>Settings</span>
      </button>

      {/* ===== ORG VIEW TOGGLE ===== */}
      <button 
        onClick={() => setShowReportingLines(!showReportingLines)} 
        style={{
          position: 'fixed',
          top: '32px',
          left: '170px',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '14px 24px',
          background: showReportingLines ? 'rgba(0, 212, 255, 0.15)' : 'rgba(0, 212, 255, 0.05)',
          backdropFilter: 'blur(20px)',
          border: showReportingLines ? '1px solid #00d4ff' : '1px solid rgba(0, 212, 255, 0.3)',
          borderRadius: '4px',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          animation: 'fadeInDown 1s ease-out 0.6s both',
          boxShadow: showReportingLines ? '0 0 15px rgba(0, 212, 255, 0.3)' : 'none'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = '#00d4ff';
          e.currentTarget.style.boxShadow = '0 0 20px rgba(0, 212, 255, 0.3)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = showReportingLines ? '#00d4ff' : 'rgba(0, 212, 255, 0.3)';
          e.currentTarget.style.boxShadow = showReportingLines ? '0 0 15px rgba(0, 212, 255, 0.3)' : 'none';
        }}
      >
        <svg 
          width="18" 
          height="18" 
          fill="none" 
          stroke={showReportingLines ? '#00d4ff' : 'rgba(255,255,255,0.7)'} 
          strokeWidth="2" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
        </svg>
        <span style={{ 
          fontSize: '14px', 
          fontWeight: 600, 
          color: showReportingLines ? '#00d4ff' : '#ffffff',
          letterSpacing: '0.5px',
          textShadow: showReportingLines ? '0 0 10px rgba(0, 212, 255, 0.5)' : 'none'
        }}>Org View</span>
      </button>

      {/* ===== SETTINGS PANEL ===== */}
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        height: '100%',
        width: '380px',
        background: 'rgba(10, 15, 26, 0.98)',
        backdropFilter: 'blur(40px)',
        borderRight: '1px solid rgba(0, 212, 255, 0.2)',
        boxShadow: '20px 0 60px rgba(0,0,0,0.5), 0 0 40px rgba(0, 212, 255, 0.1)',
        transform: showSettings ? 'translateX(0)' : 'translateX(-100%)',
        transition: 'transform 0.3s ease',
        zIndex: 150,
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Panel Header */}
        <div style={{
          padding: '24px',
          borderBottom: '1px solid rgba(0, 212, 255, 0.2)',
          background: 'linear-gradient(90deg, rgba(0, 212, 255, 0.08) 0%, transparent 100%)',
          position: 'relative'
        }}>
          {/* Cyan accent line */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '2px',
            background: 'linear-gradient(90deg, transparent, #00d4ff, transparent)',
            boxShadow: '0 0 20px rgba(0, 212, 255, 0.5)'
          }} />
          
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #00d4ff, #0099cc)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 20px rgba(0, 212, 255, 0.4)'
              }}>
                <svg width="20" height="20" fill="none" stroke="#0a0f1a" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h2 style={{ 
                fontFamily: "'Orbitron', 'Inter', sans-serif",
                fontSize: '18px', 
                fontWeight: 700, 
                color: '#fff', 
                margin: 0,
                textShadow: '0 0 15px rgba(0, 212, 255, 0.3)',
                letterSpacing: '1px'
              }}>SETTINGS</h2>
            </div>
            <button
              onClick={() => setShowSettings(false)}
              style={{
                padding: '8px',
                background: 'transparent',
                border: '1px solid rgba(0, 212, 255, 0.2)',
                borderRadius: '4px',
                cursor: 'pointer',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(0, 212, 255, 0.1)';
                e.currentTarget.style.borderColor = '#00d4ff';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.borderColor = 'rgba(0, 212, 255, 0.2)';
              }}
            >
              <svg width="18" height="18" fill="none" stroke="#00d4ff" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p style={{ 
            fontSize: '11px', 
            color: 'rgba(0, 212, 255, 0.6)', 
            marginTop: '8px',
            textTransform: 'uppercase',
            letterSpacing: '1.5px'
          }}>Customize your experience</p>
        </div>

        {/* Settings Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Glow Intensity */}
          <div style={{
            padding: '20px',
            background: 'rgba(0, 212, 255, 0.03)',
            borderRadius: '8px',
            border: '1px solid rgba(0, 212, 255, 0.1)'
          }}>
            <label style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px', 
              fontSize: '13px', 
              fontWeight: 600, 
              color: '#fff', 
              marginBottom: '14px',
              textTransform: 'uppercase',
              letterSpacing: '1px'
            }}>
              <span style={{ 
                width: '8px', 
                height: '8px', 
                borderRadius: '50%', 
                background: '#00d4ff', 
                boxShadow: '0 0 10px #00d4ff',
                animation: 'statusPulse 2s ease-in-out infinite' 
              }} />
              Glow Intensity: {Math.round(settings.glowIntensity * 100)}%
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={settings.glowIntensity}
              onChange={(e) => setSettings({ ...settings, glowIntensity: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: '#00d4ff', height: '4px', borderRadius: '2px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'rgba(0, 212, 255, 0.5)', marginTop: '6px', textTransform: 'uppercase', letterSpacing: '1px' }}>
              <span>Off</span>
              <span>Normal</span>
              <span>Intense</span>
            </div>
          </div>

          {/* Animation Speed */}
          <div style={{
            padding: '20px',
            background: 'rgba(0, 212, 255, 0.03)',
            borderRadius: '8px',
            border: '1px solid rgba(0, 212, 255, 0.1)'
          }}>
            <label style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px', 
              fontSize: '13px', 
              fontWeight: 600, 
              color: '#fff', 
              marginBottom: '14px',
              textTransform: 'uppercase',
              letterSpacing: '1px'
            }}>
              <span style={{ 
                width: '8px', 
                height: '8px', 
                borderRadius: '50%', 
                background: '#2ed573', 
                boxShadow: '0 0 10px #2ed573',
                animation: 'statusPulse 2s ease-in-out infinite' 
              }} />
              Animation Speed: {settings.animationSpeed}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={settings.animationSpeed}
              onChange={(e) => setSettings({ ...settings, animationSpeed: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: '#2ed573', height: '4px', borderRadius: '2px' }}
            />
          </div>

          {/* Particle Density */}
          <div style={{
            padding: '20px',
            background: 'rgba(0, 212, 255, 0.03)',
            borderRadius: '8px',
            border: '1px solid rgba(0, 212, 255, 0.1)'
          }}>
            <label style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px', 
              fontSize: '13px', 
              fontWeight: 600, 
              color: '#fff', 
              marginBottom: '14px',
              textTransform: 'uppercase',
              letterSpacing: '1px'
            }}>
              <span style={{ 
                width: '8px', 
                height: '8px', 
                borderRadius: '50%', 
                background: '#a55eea', 
                boxShadow: '0 0 10px #a55eea',
                animation: 'statusPulse 2s ease-in-out infinite' 
              }} />
              Grid Density: {settings.particleDensity}
            </label>
            <input
              type="range"
              min="0"
              max="8"
              step="1"
              value={settings.particleDensity}
              onChange={(e) => setSettings({ ...settings, particleDensity: parseInt(e.target.value) })}
              style={{ width: '100%', accentColor: '#a55eea', height: '4px', borderRadius: '2px' }}
            />
          </div>

          {/* Brightness */}
          <div style={{
            padding: '20px',
            background: 'rgba(0, 212, 255, 0.03)',
            borderRadius: '8px',
            border: '1px solid rgba(0, 212, 255, 0.1)'
          }}>
            <label style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px', 
              fontSize: '13px', 
              fontWeight: 600, 
              color: '#fff', 
              marginBottom: '14px',
              textTransform: 'uppercase',
              letterSpacing: '1px'
            }}>
              <span style={{ 
                width: '8px', 
                height: '8px', 
                borderRadius: '50%', 
                background: '#ffa502', 
                boxShadow: '0 0 10px #ffa502',
                animation: 'statusPulse 2s ease-in-out infinite' 
              }} />
              Brightness: {Math.round(settings.brightness * 100)}%
            </label>
            <input
              type="range"
              min="0.5"
              max="1.5"
              step="0.1"
              value={settings.brightness}
              onChange={(e) => setSettings({ ...settings, brightness: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: '#ffa502', height: '4px', borderRadius: '2px' }}
            />
          </div>

          {/* Effects Toggle */}
          <div
            onClick={() => setSettings({ ...settings, effectsEnabled: !settings.effectsEnabled })}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '20px',
              background: 'rgba(0, 212, 255, 0.03)',
              borderRadius: '8px',
              border: '1px solid rgba(0, 212, 255, 0.1)',
              cursor: 'pointer',
              transition: 'all 0.3s ease'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '20px' }}>⚡</span>
              <div>
                <p style={{ fontSize: '13px', fontWeight: 600, color: '#fff', margin: 0, textTransform: 'uppercase', letterSpacing: '1px' }}>Enable Effects</p>
                <p style={{ fontSize: '10px', color: 'rgba(0, 212, 255, 0.5)', margin: 0, marginTop: '4px' }}>Animations & Glows</p>
              </div>
            </div>
            <div style={{
              width: '48px',
              height: '26px',
              borderRadius: '13px',
              background: settings.effectsEnabled ? '#00d4ff' : 'rgba(255,255,255,0.2)',
              boxShadow: settings.effectsEnabled ? '0 0 15px rgba(0, 212, 255, 0.5)' : 'none',
              transition: 'all 0.3s ease',
              position: 'relative'
            }}>
              <div style={{
                width: '22px',
                height: '22px',
                borderRadius: '50%',
                background: settings.effectsEnabled ? '#0a0f1a' : '#fff',
                boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                position: 'absolute',
                top: '2px',
                left: settings.effectsEnabled ? '24px' : '2px',
                transition: 'left 0.3s ease'
              }} />
            </div>
          </div>

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
              padding: '16px',
              background: 'rgba(255, 71, 87, 0.1)',
              border: '1px solid rgba(255, 71, 87, 0.3)',
              borderRadius: '4px',
              color: '#ff4757',
              fontSize: '13px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              transition: 'all 0.3s ease',
              textTransform: 'uppercase',
              letterSpacing: '1px'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255, 71, 87, 0.2)';
              e.currentTarget.style.boxShadow = '0 0 20px rgba(255, 71, 87, 0.3)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 71, 87, 0.1)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Reset Defaults
          </button>
        </div>

        {/* Panel Footer */}
        <div style={{
          padding: '16px',
          borderTop: '1px solid rgba(0, 212, 255, 0.1)',
          background: 'rgba(0, 212, 255, 0.02)',
          textAlign: 'center'
        }}>
          <p style={{ 
            fontFamily: "'Orbitron', 'Inter', sans-serif",
            fontSize: '10px', 
            color: 'rgba(0, 212, 255, 0.4)', 
            margin: 0,
            letterSpacing: '2px'
          }}>NEXUS COMMAND v1.0</p>
        </div>
      </div>

      {/* Settings Overlay */}
      {showSettings && (
        <div 
          onClick={() => setShowSettings(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(10, 15, 26, 0.5)',
            zIndex: 140
          }}
        />
      )}

      {/* ===== MAIN CONTENT ===== */}
      <div style={{
        position: 'relative',
        zIndex: 10,
        width: '95%',
        maxWidth: '2200px',
        textAlign: 'center',
        margin: '0 auto'
      }}>
        {/* ===== COMMANDER BADGE ===== */}
        <div style={{
          position: 'fixed',
          top: '50px',
          right: '48px',
          display: 'flex',
          alignItems: 'center',
          gap: '20px',
          padding: '16px 28px 16px 16px',
          borderRadius: '8px',
          background: 'rgba(0, 212, 255, 0.05)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(0, 212, 255, 0.3)',
          boxShadow: '0 0 30px rgba(0, 212, 255, 0.1)',
          zIndex: 100,
          animation: 'fadeInDown 1s ease-out 0.5s both'
        }}>
          {/* Accent line */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: '20%',
            right: '20%',
            height: '2px',
            background: 'linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.5), transparent)'
          }} />
          
          {/* Commander Avatar */}
          <div style={{ position: 'relative' }}>
            {settings.effectsEnabled && (
              <div style={{
                position: 'absolute',
                inset: '-4px',
                borderRadius: '50%',
                background: '#00d4ff',
                opacity: 0.3 * settings.glowIntensity,
                filter: `blur(${8 * settings.glowIntensity}px)`,
                animation: `techPulse ${3 / settings.animationSpeed}s ease-in-out infinite`
              }} />
            )}
            <div style={{
              position: 'relative',
              width: '100px',
              height: '100px',
              borderRadius: '50%',
              overflow: 'hidden',
              border: '2px solid rgba(0, 212, 255, 0.4)',
              boxShadow: '0 0 20px rgba(0, 212, 255, 0.3)'
            }}>
              <img src={commanderImg} alt="Commander" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
            {/* Online Indicator */}
            <div style={{
              position: 'absolute',
              bottom: '2px',
              right: '2px',
              width: '14px',
              height: '14px',
              borderRadius: '50%',
              background: '#2ed573',
              border: '2px solid #0a0f1a',
              boxShadow: '0 0 10px rgba(46, 213, 115, 0.6)'
            }} />
          </div>
          
          {/* Commander Info */}
          <div style={{ textAlign: 'left' }}>
            <p style={{ 
              fontSize: '11px', 
              fontWeight: 500, 
              color: 'rgba(0, 212, 255, 0.7)',
              lineHeight: 1.2,
              letterSpacing: '2px',
              textTransform: 'uppercase',
              marginBottom: '6px'
            }}>AI Strategy</p>
            <p style={{ 
              fontFamily: "'Orbitron', 'Inter', sans-serif",
              fontSize: '22px', 
              fontWeight: 700, 
              color: '#fff',
              lineHeight: 1.1,
              textShadow: '0 0 15px rgba(0, 212, 255, 0.3)'
            }}>Carlos Guzman</p>
          </div>
        </div>

        {/* ===== HERO HEADER ===== */}
        <header style={{ 
          textAlign: 'center', 
          marginBottom: '60px',
          padding: '60px 40px',
          background: 'linear-gradient(135deg, rgba(10, 15, 26, 0.8) 0%, rgba(13, 21, 37, 0.8) 50%, rgba(10, 15, 26, 0.8) 100%)',
          borderRadius: '8px',
          border: '1px solid rgba(0, 212, 255, 0.2)',
          position: 'relative',
          overflow: 'hidden'
        }}>
          {/* Top accent line */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '2px',
            background: 'linear-gradient(90deg, transparent, #00d4ff, transparent)',
            boxShadow: '0 0 30px rgba(0, 212, 255, 0.5)'
          }} />
          
          {/* Circuit decoration */}
          <div style={{
            position: 'absolute',
            bottom: '15%',
            right: '5%',
            width: '200px',
            height: '100px',
            border: '1px solid rgba(0, 212, 255, 0.2)',
            borderRight: 'none',
            borderBottom: 'none',
            opacity: 0.5
          }} />
          
          <h1 style={{
            fontFamily: "'Orbitron', 'Inter', sans-serif",
            fontSize: 'clamp(48px, 8vw, 96px)',
            fontWeight: 900,
            letterSpacing: '2px',
            lineHeight: 1.1,
            marginBottom: '24px',
            color: '#ffffff',
            textShadow: `
              0 0 10px rgba(255, 255, 255, 0.5),
              0 0 30px rgba(0, 212, 255, 0.5),
              0 0 60px rgba(0, 212, 255, 0.3)
            `
          }}>
            Agentic Cognitive Enterprise 
          </h1>
          
          <p style={{
            fontFamily: "'Orbitron', 'Inter', sans-serif",
            fontSize: '24px',
            fontWeight: 500,
            color: 'rgba(255,255,255,0.8)',
            marginBottom: '12px',
            letterSpacing: '3px',
            textTransform: 'uppercase'
          }}>Multi-Agent Intelligence Platform</p>
          
          <p style={{
            fontSize: '16px',
            fontWeight: 400,
            color: 'rgba(0, 212, 255, 0.7)',
            letterSpacing: '1px'
          }}>Think different. Think together.</p>
        </header>

        {/* ===== TEAM LAYOUT ===== */}
        <div style={{ marginBottom: '60px', marginTop: '30px', position: 'relative' }}>
          
          {/* TIER 1: Leadership Row */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'flex-start',
            gap: '50px',
            marginBottom: '30px',
            position: 'relative',
            minHeight: '320px'
          }}>
            {/* Gears */}
            <div style={{ transform: 'scale(0.95)', width: '220px', flexShrink: 0, alignSelf: 'flex-start', paddingTop: '50px' }}>
              <TeamMemberCard agent={agents.gears} settings={settings} delay="0.8s" hideDescription={showReportingLines} />
            </div>

            {/* Nexus - Leader */}
            <div style={{ transform: 'scale(1.1)', zIndex: 10, width: '280px', flexShrink: 0, alignSelf: 'flex-start' }}>
              <TeamMemberCard agent={agents.nexus} isLeader={true} settings={settings} delay="0.3s" hideDescription={showReportingLines} />
            </div>

            {/* Sentinel */}
            <div style={{ transform: 'scale(0.95)', width: '220px', flexShrink: 0, alignSelf: 'flex-start', paddingTop: '50px' }}>
              <TeamMemberCard agent={agents.sentinel} settings={settings} delay="1.0s" hideDescription={showReportingLines} />
            </div>
          </div>

          {/* Tier Divider */}
          {!showReportingLines && (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '16px', 
              maxWidth: '1900px', 
              margin: '0 auto 40px auto',
              padding: '0 20px'
            }}>
              <div style={{ flex: 1, height: '1px', background: 'linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.4), transparent)' }} />
              <span style={{ 
                fontFamily: "'Orbitron', 'Inter', sans-serif",
                color: '#00d4ff', 
                fontSize: '14px', 
                fontWeight: 700, 
                letterSpacing: '4px',
                textShadow: '0 0 15px rgba(0, 212, 255, 0.5)'
              }}>CORE AGENTS</span>
              <div style={{ flex: 1, height: '1px', background: 'linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.4), transparent)' }} />
            </div>
          )}

          {/* Reporting Lines SVG */}
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
                <linearGradient id="cyanGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#00d4ff" />
                  <stop offset="50%" stopColor="#00ffff" />
                  <stop offset="100%" stopColor="#00d4ff" />
                </linearGradient>
                <filter id="cyanGlow" x="-100%" y="-100%" width="300%" height="300%">
                  <feGaussianBlur stdDeviation="3" result="blur1"/>
                  <feGaussianBlur stdDeviation="6" result="blur2"/>
                  <feMerge>
                    <feMergeNode in="blur2"/>
                    <feMergeNode in="blur1"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>

              {/* Horizontal line connecting leadership */}
              <rect 
                x="38.5%" 
                y="360px" 
                width="23%" 
                height="2px"
                fill="#00d4ff"
                rx="1"
                filter="url(#cyanGlow)"
              />

              {/* Leadership nodes */}
              <circle cx="38.5%" cy="360px" r="6" fill="#00d4ff" filter="url(#cyanGlow)" />
              <circle cx="50%" cy="360px" r="6" fill="#00d4ff" filter="url(#cyanGlow)" />
              <circle cx="61.5%" cy="360px" r="6" fill="#00d4ff" filter="url(#cyanGlow)" />

              {/* Vertical lines to core agents */}
              <rect x="35%" y="540px" width="1.5px" height="125px" fill="#00d4ff" filter="url(#cyanGlow)" />
              <circle cx="35%" cy="540px" r="5" fill="#00d4ff" filter="url(#cyanGlow)" />

              <rect x="50%" y="575px" width="1.5px" height="90px" fill="#00d4ff" filter="url(#cyanGlow)" />
              <circle cx="50%" cy="575px" r="5" fill="#00d4ff" filter="url(#cyanGlow)" />

              <rect x="66%" y="540px" width="1.5px" height="125px" fill="#00d4ff" filter="url(#cyanGlow)" />
              <circle cx="66%" cy="540px" r="5" fill="#00d4ff" filter="url(#cyanGlow)" />

              {/* Horizontal line across core agents */}
              <rect x="9.5%" y="664px" width="81.5%" height="2px" fill="#00d4ff" rx="1" filter="url(#cyanGlow)" />

              {/* Core agent end nodes */}
              <circle cx="9.5%" cy="665px" r="5" fill="#00d4ff" filter="url(#cyanGlow)" />
              <circle cx="91%" cy="665px" r="5" fill="#00d4ff" filter="url(#cyanGlow)" />
            </svg>
          )}

          {/* TIER 2: Core Agents Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(7, 1fr)',
            gap: '30px',
            maxWidth: '1900px',
            margin: '0 auto',
            padding: '80px 20px 40px'
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

        {/* ===== CHAT INTERFACE ===== */}
        <div style={{ 
          maxWidth: '1200px', 
          margin: '0 auto',
          animation: 'fadeInUp 1s ease-out 1s both'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '18px',
            padding: '24px 32px',
            background: 'rgba(0, 212, 255, 0.03)',
            borderRadius: '8px',
            border: '1px solid rgba(0, 212, 255, 0.2)',
            transition: 'all 0.3s ease'
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = '#00d4ff';
            e.currentTarget.style.boxShadow = '0 0 30px rgba(0, 212, 255, 0.2)';
          }}
          >
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
                color: '#ffffff',
                fontSize: '24px',
                fontWeight: 400,
                fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
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
                width: '56px',
                height: '56px',
                borderRadius: '8px',
                background: isLoading || !message.trim() 
                  ? 'rgba(0, 212, 255, 0.3)' 
                  : 'linear-gradient(135deg, #00d4ff 0%, #0099cc 100%)',
                border: 'none',
                cursor: isLoading || !message.trim() ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.3s ease',
                flexShrink: 0,
                boxShadow: isLoading || !message.trim() ? 'none' : '0 0 20px rgba(0, 212, 255, 0.4)'
              }}
              onMouseEnter={(e) => {
                if (!isLoading && message.trim()) {
                  e.currentTarget.style.boxShadow = '0 0 30px rgba(0, 212, 255, 0.6)';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isLoading && message.trim()) {
                  e.currentTarget.style.boxShadow = '0 0 20px rgba(0, 212, 255, 0.4)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }
              }}
            >
              <svg width="20" height="20" fill="none" stroke="#0a0f1a" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </button>
          </div>
          <p style={{
            fontFamily: "'Orbitron', 'Inter', sans-serif",
            fontSize: '11px',
            color: 'rgba(0, 212, 255, 0.6)',
            marginTop: '16px',
            textAlign: 'center',
            letterSpacing: '3px',
            textTransform: 'uppercase'
          }}>Welcome to the Future</p>
        </div>
      </div>

      {/* ===== CSS ANIMATIONS ===== */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Orbitron:wght@400;500;600;700;800;900&display=swap');
        
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
        
        @keyframes gridScroll {
          0% { transform: translate(0, 0); }
          100% { transform: translate(80px, 80px); }
        }

        @keyframes techPulse {
          0%, 100% { opacity: 0.4; transform: scale(1); }
          50% { opacity: 0.8; transform: scale(1.1); }
        }

        @keyframes statusPulse {
          0%, 100% { 
            box-shadow: 0 0 8px currentColor, 0 0 16px currentColor;
          }
          50% { 
            box-shadow: 0 0 12px currentColor, 0 0 24px currentColor, 0 0 36px currentColor;
          }
        }

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

        button:hover .settings-icon {
          transform: rotate(180deg);
        }

        input::placeholder {
          color: rgba(0, 212, 255, 0.4);
        }
      `}</style>
    </div>
  );
}
