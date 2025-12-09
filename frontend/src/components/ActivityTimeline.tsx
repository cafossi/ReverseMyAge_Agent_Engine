// ============================================================================
// ACTIVITY TIMELINE - TECH THEME
// Styled to match the Pareto Optimization Report aesthetic
// ============================================================================
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Loader2,
  Activity,
  Info,
  Search,
  TextSearch,
  Brain,
  Pen,
  ChevronDown,
  ChevronUp,
  Link,
} from "lucide-react";
import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';

// Import logo image
import MetroImg from "../../agents/metro_one_logo.png";

// ============================================================================
// TECH THEME COLORS
// ============================================================================
const THEME = {
  // Core colors
  bgPrimary: '#0a0f1a',
  bgSecondary: 'rgba(10, 15, 26, 0.95)',
  bgCard: 'rgba(0, 212, 255, 0.03)',
  
  // Accent colors
  cyan: '#00d4ff',
  cyanDark: '#0099cc',
  cyanGlow: 'rgba(0, 212, 255, 0.3)',
  cyanSubtle: 'rgba(0, 212, 255, 0.1)',
  
  // Status colors
  green: '#2ed573',
  greenGlow: 'rgba(46, 213, 115, 0.3)',
  amber: '#ffa502',
  amberGlow: 'rgba(255, 165, 2, 0.3)',
  red: '#ff4757',
  redGlow: 'rgba(255, 71, 87, 0.3)',
  blue: '#3b82f6',
  blueGlow: 'rgba(59, 130, 246, 0.3)',
  purple: '#a55eea',
  purpleGlow: 'rgba(165, 94, 234, 0.3)',
  
  // Text colors
  textPrimary: '#ffffff',
  textSecondary: 'rgba(255, 255, 255, 0.75)',
  textMuted: 'rgba(255, 255, 255, 0.5)',
  
  // Border colors
  borderSubtle: 'rgba(0, 212, 255, 0.15)',
  borderMedium: 'rgba(0, 212, 255, 0.3)',
  borderBright: '#00d4ff',
};

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================
export interface ProcessedEvent {
  title: string;
  data: any;
}

interface ActivityTimelineProps {
  processedEvents: ProcessedEvent[];
  isLoading: boolean;
  websiteCount: number;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================
export function ActivityTimeline({
  processedEvents,
  isLoading,
  websiteCount,
}: ActivityTimelineProps) {
  const [isTimelineCollapsed, setIsTimelineCollapsed] = useState<boolean>(false);

  // ============================================================================
  // DATA FORMATTING FUNCTIONS
  // ============================================================================
  const formatEventData = (data: any): string => {
    // Handle new structured data types
    if (typeof data === "object" && data !== null && data.type) {
      switch (data.type) {
        case 'functionCall':
          return `Calling function: ${data.name}\nArguments: ${JSON.stringify(data.args, null, 2)}`;
        case 'functionResponse':
          return `Function ${data.name} response:\n${JSON.stringify(data.response, null, 2)}`;
        case 'text':
          return data.content;
        case 'sources':
          const sources = data.content as Record<string, { title: string; url: string }>;
          if (Object.keys(sources).length === 0) {
            return "No sources found.";
          }
          return Object.values(sources)
            .map(source => `[${source.title || 'Untitled Source'}](${source.url})`).join(', ');
        default:
          return JSON.stringify(data, null, 2);
      }
    }
    
    // Existing logic for backward compatibility
    if (typeof data === "string") {
      try {
        const parsed = JSON.parse(data);
        return JSON.stringify(parsed, null, 2);
      } catch {
        return data;
      }
    } else if (Array.isArray(data)) {
      return data.join(", ");
    } else if (typeof data === "object" && data !== null) {
      return JSON.stringify(data, null, 2);
    }
    return String(data);
  };

  const isJsonData = (data: any): boolean => {
    if (typeof data === "object" && data !== null && data.type) {
      if (data.type === 'sources') {
        return false;
      }
      return data.type === 'functionCall' || data.type === 'functionResponse';
    }
    
    if (typeof data === "string") {
      try {
        JSON.parse(data);
        return true;
      } catch {
        return false;
      }
    }
    return typeof data === "object" && data !== null;
  };

  // ============================================================================
  // EVENT ICON MAPPING - Tech Theme Colors
  // ============================================================================
  const getEventIcon = (title: string, index: number) => {
    const iconStyle = { filter: `drop-shadow(0 0 4px ${THEME.cyanGlow})` };
    
    if (index === 0 && isLoading && processedEvents.length === 0) {
      return <Loader2 style={{ width: '16px', height: '16px', color: THEME.cyan, ...iconStyle }} className="animate-spin" />;
    }
    if (title.toLowerCase().includes("function call")) {
      return <Activity style={{ width: '16px', height: '16px', color: THEME.blue, filter: `drop-shadow(0 0 4px ${THEME.blueGlow})` }} />;
    } else if (title.toLowerCase().includes("function response")) {
      return <Activity style={{ width: '16px', height: '16px', color: THEME.green, filter: `drop-shadow(0 0 4px ${THEME.greenGlow})` }} />;
    } else if (title.toLowerCase().includes("generating")) {
      return <TextSearch style={{ width: '16px', height: '16px', color: THEME.purple, filter: `drop-shadow(0 0 4px ${THEME.purpleGlow})` }} />;
    } else if (title.toLowerCase().includes("thinking")) {
      return <Loader2 style={{ width: '16px', height: '16px', color: THEME.cyan, ...iconStyle }} className="animate-spin" />;
    } else if (title.toLowerCase().includes("reflection")) {
      return <Brain style={{ width: '16px', height: '16px', color: THEME.purple, filter: `drop-shadow(0 0 4px ${THEME.purpleGlow})` }} />;
    } else if (title.toLowerCase().includes("research")) {
      return <Search style={{ width: '16px', height: '16px', color: THEME.cyan, ...iconStyle }} />;
    } else if (title.toLowerCase().includes("finalizing")) {
      return <Pen style={{ width: '16px', height: '16px', color: THEME.green, filter: `drop-shadow(0 0 4px ${THEME.greenGlow})` }} />;
    } else if (title.toLowerCase().includes("retrieved sources")) {
      return <Link style={{ width: '16px', height: '16px', color: THEME.amber, filter: `drop-shadow(0 0 4px ${THEME.amberGlow})` }} />;
    }
    return <Activity style={{ width: '16px', height: '16px', color: THEME.cyan, ...iconStyle }} />;
  };

  // ============================================================================
  // RENDER
  // ============================================================================
  return (
    <div
      style={{
        position: 'relative',
        background: THEME.bgSecondary,
        border: `1px solid ${THEME.borderSubtle}`,
        borderRadius: '8px',
        maxWidth: '100%',
        overflow: 'hidden',
        boxShadow: `0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 ${THEME.borderSubtle}`,
        transition: 'all 0.3s ease'
      }}
    >
      {/* Top accent line */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: '2px',
        background: `linear-gradient(90deg, transparent, ${THEME.cyan}, transparent)`,
        boxShadow: `0 0 15px ${THEME.cyanGlow}`
      }} />

      {/* ===== HEADER ===== */}
      <div
        onClick={() => setIsTimelineCollapsed(!isTimelineCollapsed)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.875rem 1.25rem',
          cursor: 'pointer',
          background: isTimelineCollapsed ? 'transparent' : `linear-gradient(180deg, ${THEME.cyanSubtle} 0%, transparent 100%)`,
          borderBottom: isTimelineCollapsed ? 'none' : `1px solid ${THEME.borderSubtle}`,
          transition: 'all 0.3s ease'
        }}
      >
        {/* Left: Logo and Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* Logo with glow */}
          <div style={{
            position: 'relative',
            width: '44px',
            height: '44px',
            borderRadius: '50%',
            overflow: 'hidden',
            border: `2px solid ${THEME.borderMedium}`,
            boxShadow: `0 0 20px ${THEME.cyanGlow}`
          }}>
            <img 
              src={MetroImg}
              alt="EPC"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                filter: `drop-shadow(0 0 8px ${THEME.cyanGlow})`
              }}
            />
          </div>

          {/* Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <span style={{
              fontFamily: "'Orbitron', 'Inter', sans-serif",
              fontSize: '1rem',
              fontWeight: 700,
              color: THEME.textPrimary,
              textShadow: `0 0 10px ${THEME.cyanGlow}`,
              letterSpacing: '1px'
            }}>
              EPC
            </span>
            <span style={{
              width: '2px',
              height: '18px',
              background: THEME.cyan,
              boxShadow: `0 0 8px ${THEME.cyan}`,
              borderRadius: '1px'
            }} />
            <span style={{
              fontSize: '0.8rem',
              fontWeight: 600,
              color: THEME.textSecondary,
              letterSpacing: '0.5px'
            }}>
              Performance Excellence Team
            </span>
          </div>

          {/* Website count badge */}
          {websiteCount > 0 && (
            <span style={{
              marginLeft: '0.5rem',
              padding: '0.25rem 0.625rem',
              background: THEME.cyanSubtle,
              border: `1px solid ${THEME.borderMedium}`,
              borderRadius: '4px',
              fontSize: '0.7rem',
              fontWeight: 600,
              color: THEME.cyan,
              letterSpacing: '0.5px'
            }}>
              {websiteCount} websites
            </span>
          )}

          {/* Processing indicator */}
          {isLoading && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.375rem',
              marginLeft: '0.5rem',
              padding: '0.25rem 0.625rem',
              background: 'rgba(46, 213, 115, 0.1)',
              border: '1px solid rgba(46, 213, 115, 0.3)',
              borderRadius: '4px'
            }}>
              <div style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: THEME.green,
                boxShadow: `0 0 8px ${THEME.green}`,
                animation: 'statusPulse 1.5s ease-in-out infinite'
              }} />
              <span style={{ fontSize: '0.7rem', fontWeight: 600, color: THEME.green, letterSpacing: '0.5px' }}>
                PROCESSING
              </span>
            </div>
          )}
        </div>

        {/* Right: Collapse toggle */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.375rem 0.75rem',
          background: THEME.bgCard,
          border: `1px solid ${THEME.borderSubtle}`,
          borderRadius: '4px',
          transition: 'all 0.3s ease'
        }}>
          <span style={{ fontSize: '0.7rem', color: THEME.textMuted, textTransform: 'uppercase', letterSpacing: '1px' }}>
            {isTimelineCollapsed ? 'Expand' : 'Collapse'}
          </span>
          {isTimelineCollapsed ? (
            <ChevronDown style={{ width: '14px', height: '14px', color: THEME.cyan }} />
          ) : (
            <ChevronUp style={{ width: '14px', height: '14px', color: THEME.cyan }} />
          )}
        </div>
      </div>

      {/* ===== TIMELINE CONTENT ===== */}
      {!isTimelineCollapsed && (
        <div style={{ maxHeight: '70vh', overflowY: 'auto', padding: '1rem 1.25rem' }}>
          
          {/* Initial loading state */}
          {isLoading && processedEvents.length === 0 && (
            <div style={{ position: 'relative', paddingLeft: '2.5rem', paddingBottom: '1rem' }}>
              {/* Timeline connector line */}
              <div style={{
                position: 'absolute',
                left: '0.875rem',
                top: '1.25rem',
                bottom: 0,
                width: '2px',
                background: `linear-gradient(180deg, ${THEME.cyan} 0%, ${THEME.borderSubtle} 100%)`
              }} />
              
              {/* Event node */}
              <div style={{
                position: 'absolute',
                left: 0,
                top: '0.5rem',
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: THEME.bgPrimary,
                border: `2px solid ${THEME.cyan}`,
                boxShadow: `0 0 15px ${THEME.cyanGlow}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Loader2 style={{ width: '14px', height: '14px', color: THEME.cyan }} className="animate-spin" />
              </div>
              
              {/* Event content */}
              <div style={{
                padding: '0.5rem 0.75rem',
                background: THEME.bgCard,
                border: `1px solid ${THEME.borderSubtle}`,
                borderRadius: '6px',
                marginLeft: '0.5rem'
              }}>
                <p style={{
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: THEME.cyan,
                  margin: 0,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  <span style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: THEME.cyan,
                    boxShadow: `0 0 8px ${THEME.cyan}`,
                    animation: 'statusPulse 1s ease-in-out infinite'
                  }} />
                  Thinking...
                </p>
              </div>
            </div>
          )}

          {/* Events list */}
          {processedEvents.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
              {processedEvents.map((eventItem, index) => (
                <div key={index} style={{ position: 'relative', paddingLeft: '2.5rem', paddingBottom: '1rem' }}>
                  
                  {/* Timeline connector line */}
                  {(index < processedEvents.length - 1 || (isLoading && index === processedEvents.length - 1)) && (
                    <div style={{
                      position: 'absolute',
                      left: '0.9375rem',
                      top: '2rem',
                      bottom: 0,
                      width: '2px',
                      background: `linear-gradient(180deg, ${THEME.borderMedium} 0%, ${THEME.borderSubtle} 100%)`
                    }} />
                  )}
                  
                  {/* Event node */}
                  <div style={{
                    position: 'absolute',
                    left: 0,
                    top: '0.375rem',
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: THEME.bgPrimary,
                    border: `2px solid ${THEME.borderMedium}`,
                    boxShadow: `0 0 10px ${THEME.cyanGlow}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.3s ease'
                  }}>
                    {getEventIcon(eventItem.title, index)}
                  </div>
                  
                  {/* Event content */}
                  <div style={{
                    background: THEME.bgCard,
                    border: `1px solid ${THEME.borderSubtle}`,
                    borderRadius: '6px',
                    overflow: 'hidden',
                    marginLeft: '0.5rem',
                    transition: 'all 0.3s ease'
                  }}>
                    {/* Event header */}
                    <div style={{
                      padding: '0.625rem 0.875rem',
                      borderBottom: eventItem.data ? `1px solid ${THEME.borderSubtle}` : 'none',
                      background: `linear-gradient(90deg, ${THEME.cyanSubtle} 0%, transparent 100%)`
                    }}>
                      <p style={{
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        color: THEME.textPrimary,
                        margin: 0,
                        letterSpacing: '0.25px'
                      }}>
                        {eventItem.title}
                      </p>
                    </div>
                    
                    {/* Event data */}
                    {eventItem.data && (
                      <div style={{ padding: '0.625rem 0.875rem' }}>
                        {isJsonData(eventItem.data) ? (
                          <pre style={{
                            background: THEME.bgPrimary,
                            border: `1px solid ${THEME.borderSubtle}`,
                            borderRadius: '4px',
                            padding: '0.75rem',
                            margin: 0,
                            fontSize: '0.75rem',
                            fontFamily: "'Courier New', monospace",
                            color: THEME.textSecondary,
                            overflowX: 'auto',
                            whiteSpace: 'pre-wrap',
                            lineHeight: 1.5
                          }}>
                            {formatEventData(eventItem.data)}
                          </pre>
                        ) : (
                          <div style={{ fontSize: '0.8rem', color: THEME.textSecondary, lineHeight: 1.6 }}>
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm, remarkBreaks]}
                              components={{
                                p: ({ children }) => (
                                  <span style={{ display: 'inline' }}>{children}</span>
                                ),
                                a: ({ href, children }) => (
                                  <a
                                    href={href}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{
                                      color: THEME.cyan,
                                      textDecoration: 'none',
                                      borderBottom: `1px solid ${THEME.cyanGlow}`,
                                      transition: 'all 0.2s ease'
                                    }}
                                  >
                                    {children}
                                  </a>
                                ),
                                code: ({ children }) => (
                                  <code style={{
                                    background: THEME.cyanSubtle,
                                    padding: '2px 6px',
                                    borderRadius: '3px',
                                    fontSize: '0.75rem',
                                    fontFamily: "'Courier New', monospace",
                                    color: THEME.amber,
                                    border: `1px solid ${THEME.borderSubtle}`
                                  }}>
                                    {children}
                                  </code>
                                ),
                              }}
                            >
                              {formatEventData(eventItem.data)}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {/* Ongoing thinking indicator */}
              {isLoading && processedEvents.length > 0 && (
                <div style={{ position: 'relative', paddingLeft: '2.5rem', paddingBottom: '0.5rem' }}>
                  {/* Event node */}
                  <div style={{
                    position: 'absolute',
                    left: 0,
                    top: '0.375rem',
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: THEME.bgPrimary,
                    border: `2px solid ${THEME.cyan}`,
                    boxShadow: `0 0 15px ${THEME.cyanGlow}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <Loader2 style={{ width: '14px', height: '14px', color: THEME.cyan }} className="animate-spin" />
                  </div>
                  
                  {/* Content */}
                  <div style={{
                    padding: '0.625rem 0.875rem',
                    background: THEME.bgCard,
                    border: `1px solid ${THEME.borderSubtle}`,
                    borderRadius: '6px',
                    marginLeft: '0.5rem'
                  }}>
                    <p style={{
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      color: THEME.cyan,
                      margin: 0,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}>
                      <span style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background: THEME.cyan,
                        boxShadow: `0 0 8px ${THEME.cyan}`,
                        animation: 'statusPulse 1s ease-in-out infinite'
                      }} />
                      Thinking...
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Empty state */}
          {!isLoading && processedEvents.length === 0 && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '3rem 1.5rem',
              textAlign: 'center'
            }}>
              <div style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                background: THEME.bgCard,
                border: `1px solid ${THEME.borderSubtle}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1rem'
              }}>
                <Info style={{ width: '24px', height: '24px', color: THEME.textMuted }} />
              </div>
              <p style={{
                fontSize: '0.9rem',
                fontWeight: 600,
                color: THEME.textMuted,
                margin: 0,
                marginBottom: '0.375rem'
              }}>
                No activity to display
              </p>
              <p style={{
                fontSize: '0.75rem',
                color: THEME.textMuted,
                opacity: 0.7,
                margin: 0
              }}>
                Timeline will update during processing
              </p>
            </div>
          )}
        </div>
      )}

      {/* ===== CSS ANIMATIONS ===== */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&display=swap');
        
        @keyframes statusPulse {
          0%, 100% { 
            box-shadow: 0 0 8px currentColor;
            opacity: 1;
          }
          50% { 
            box-shadow: 0 0 16px currentColor, 0 0 24px currentColor;
            opacity: 0.7;
          }
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .animate-spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
}
