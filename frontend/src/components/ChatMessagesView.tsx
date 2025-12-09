// ============================================================================
// IMPORTS SECTION
// ============================================================================
import type React from "react";
import { useState, ReactNode } from "react";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

import { Loader2, Copy, CopyCheck, Download, Pin } from "lucide-react";

import { InputForm } from "@/components/InputForm";
import { ActivityTimeline } from "@/components/ActivityTimeline";

import ReactMarkdown from "react-markdown";
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

import { jsPDF } from "jspdf";

import { cn } from "@/utils";

// Agent profile images
import NexusImg from "../../agents/ACE_Nexus.png";
import SentinelImg from "../../agents/ACE_Sentinel.png";
import GearsImg from "../../agents/ACE_Gears.png";

import AtlasImg from "../../agents/ACE_Atlas.png";
import MaestroImg from "../../agents/ACE_Maestro.png";
import PulseImg from "../../agents/ACE_Pulse.png";
import AegisImg from "../../agents/ACE_Aegis.png";
import SageImg from "../../agents/ACE_Sage.png";
import LexiImg from "../../agents/ACE_Lexi.png";
import ScoutImg from "../../agents/ACE_Scout.png";

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================
type MdComponentProps = {
  className?: string;
  children?: ReactNode;
  [key: string]: any;
};

interface ProcessedEvent {
  title: string;
  data: any;
}

// ============================================================================
// TECH THEME COLORS - Matching the Report Style
// ============================================================================
const THEME = {
  // Core colors
  bgPrimary: '#0a0f1a',
  bgSecondary: 'rgba(10, 15, 26, 0.8)',
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
// MARKDOWN COMPONENTS - TECH THEME STYLED
// ============================================================================
const mdComponents = {
  h1: ({ className, children, ...props }: MdComponentProps) => (
    <h1 
      style={{
        fontFamily: "'Orbitron', 'Inter', sans-serif",
        fontSize: '1.75rem',
        fontWeight: 700,
        marginTop: '1.5rem',
        marginBottom: '0.75rem',
        color: THEME.textPrimary,
        textShadow: `0 0 10px ${THEME.cyanGlow}`,
        letterSpacing: '1px',
        paddingBottom: '0.5rem',
        borderBottom: `2px solid ${THEME.cyan}`
      }} 
      {...props}
    >
      {children}
    </h1>
  ),
  
  h2: ({ className, children, ...props }: MdComponentProps) => (
    <h2 
      style={{
        fontFamily: "'Orbitron', 'Inter', sans-serif",
        fontSize: '1.4rem',
        fontWeight: 700,
        marginTop: '1.25rem',
        marginBottom: '0.5rem',
        color: THEME.textPrimary,
        textShadow: `0 0 8px ${THEME.cyanGlow}`,
        letterSpacing: '0.5px',
        paddingBottom: '0.375rem',
        borderBottom: `1px solid ${THEME.borderSubtle}`
      }} 
      {...props}
    >
      {children}
    </h2>
  ),
  
  h3: ({ className, children, ...props }: MdComponentProps) => (
    <h3 
      style={{
        fontFamily: "'Orbitron', 'Inter', sans-serif",
        fontSize: '1.15rem',
        fontWeight: 700,
        marginTop: '1rem',
        marginBottom: '0.375rem',
        color: THEME.cyan,
        textShadow: `0 0 6px ${THEME.cyanGlow}`,
        letterSpacing: '0.5px'
      }} 
      {...props}
    >
      {children}
    </h3>
  ),
  
  p: ({ className, children, ...props }: MdComponentProps) => (
    <p 
      style={{
        marginBottom: '0.875rem',
        lineHeight: 1.8,
        color: THEME.textSecondary
      }} 
      {...props}
    >
      {children}
    </p>
  ),
  
  a: ({ className, children, href, ...props }: MdComponentProps) => (
    <a
      style={{
        color: THEME.cyan,
        textDecoration: 'none',
        borderBottom: `1px solid ${THEME.cyanGlow}`,
        padding: '2px 4px',
        borderRadius: '3px',
        transition: 'all 0.2s ease'
      }}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onMouseEnter={(e) => {
        e.currentTarget.style.background = THEME.cyanSubtle;
        e.currentTarget.style.borderBottomColor = THEME.cyan;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'transparent';
        e.currentTarget.style.borderBottomColor = THEME.cyanGlow;
      }}
      {...props}
    >
      {children}
    </a>
  ),
  
  ul: ({ className, children, ...props }: MdComponentProps) => (
    <ul 
      style={{
        listStyleType: 'disc',
        paddingLeft: '1.5rem',
        marginBottom: '1rem',
        color: THEME.textSecondary
      }} 
      {...props}
    >
      {children}
    </ul>
  ),
  
  ol: ({ className, children, ...props }: MdComponentProps) => (
    <ol 
      style={{
        listStyleType: 'decimal',
        paddingLeft: '1.5rem',
        marginBottom: '1rem',
        color: THEME.textSecondary
      }} 
      {...props}
    >
      {children}
    </ol>
  ),
  
  li: ({ className, children, ...props }: MdComponentProps) => (
    <li 
      style={{
        lineHeight: 1.7,
        marginBottom: '0.375rem',
        color: THEME.textSecondary
      }}
      {...props}
    >
      {children}
    </li>
  ),
  
  blockquote: ({ className, children, ...props }: MdComponentProps) => (
    <blockquote
      style={{
        borderLeft: `4px solid ${THEME.cyan}`,
        paddingLeft: '1rem',
        fontStyle: 'italic',
        margin: '1rem 0',
        color: THEME.textSecondary,
        background: THEME.cyanSubtle,
        padding: '1rem',
        borderRadius: '0 8px 8px 0'
      }}
      {...props}
    >
      {children}
    </blockquote>
  ),
  
  code: ({ className, children, ...props }: MdComponentProps) => (
    <code
      style={{
        background: 'rgba(0, 212, 255, 0.1)',
        borderRadius: '4px',
        padding: '2px 6px',
        fontFamily: "'Courier New', monospace",
        fontSize: '0.85rem',
        color: THEME.amber,
        border: `1px solid ${THEME.borderSubtle}`
      }}
      {...props}
    >
      {children}
    </code>
  ),
  
  pre: ({ className, children, ...props }: MdComponentProps) => (
    <pre
      style={{
        background: THEME.bgPrimary,
        padding: '1rem',
        borderRadius: '8px',
        overflowX: 'auto',
        fontFamily: "'Courier New', monospace",
        fontSize: '0.85rem',
        margin: '1rem 0',
        border: `1px solid ${THEME.borderSubtle}`
      }}
      {...props}
    >
      {children}
    </pre>
  ),
  
  hr: ({ className, ...props }: MdComponentProps) => (
    <hr 
      style={{
        border: 'none',
        borderTop: `1px solid ${THEME.borderSubtle}`,
        margin: '1.5rem 0'
      }} 
      {...props} 
    />
  ),
  
  table: ({ className, children, ...props }: MdComponentProps) => (
    <div style={{ margin: '1rem 0', overflowX: 'auto' }}>
      <table 
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          background: THEME.bgSecondary,
          borderRadius: '8px',
          overflow: 'hidden',
          border: `1px solid ${THEME.borderSubtle}`
        }} 
        {...props}
      >
        {children}
      </table>
    </div>
  ),
  
  th: ({ className, children, ...props }: MdComponentProps) => (
    <th
      style={{
        background: THEME.cyanSubtle,
        color: THEME.cyan,
        fontWeight: 700,
        padding: '0.875rem 1rem',
        textAlign: 'left',
        borderBottom: `2px solid ${THEME.cyan}`,
        fontSize: '0.8rem',
        letterSpacing: '1px',
        textTransform: 'uppercase'
      }}
      {...props}
    >
      {children}
    </th>
  ),
  
  td: ({ className, children, ...props }: MdComponentProps) => (
    <td
      style={{
        padding: '0.75rem 1rem',
        borderBottom: `1px solid ${THEME.borderSubtle}`,
        color: THEME.textSecondary
      }}
      {...props}
    >
      {children}
    </td>
  ),
};

// ============================================================================
// HUMAN MESSAGE BUBBLE - TECH THEME
// ============================================================================
interface HumanMessageBubbleProps {
  message: { content: string; id: string };
  mdComponents: typeof mdComponents;
}

const HumanMessageBubble: React.FC<HumanMessageBubbleProps> = ({
  message,
  mdComponents,
}) => {
  return (
    <div style={{
      background: `linear-gradient(135deg, ${THEME.cyan} 0%, ${THEME.cyanDark} 100%)`,
      color: THEME.bgPrimary,
      borderRadius: '8px',
      padding: '1rem 1.25rem',
      maxWidth: '75%',
      boxShadow: `0 0 20px ${THEME.cyanGlow}`,
      position: 'relative'
    }}>
      {/* Top accent line */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: '20%',
        right: '20%',
        height: '2px',
        background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)'
      }} />
      <div style={{ fontWeight: 500, fontSize: '0.95rem', lineHeight: 1.6 }}>
        {message.content}
      </div>
    </div>
  );
};

// ============================================================================
// AI MESSAGE BUBBLE - TECH THEME
// ============================================================================
interface AiMessageBubbleProps {
  message: { content: string; id: string };
  mdComponents: typeof mdComponents;
  handleCopy: (text: string, messageId: string) => void;
  copiedMessageId: string | null;
  agent?: string;
  finalReportWithCitations?: boolean;
  processedEvents: ProcessedEvent[];
  websiteCount: number;
  isLoading: boolean;
}

const AiMessageBubble: React.FC<AiMessageBubbleProps> = ({
  message,
  mdComponents,
  handleCopy,
  copiedMessageId,
  agent,
  finalReportWithCitations,
  processedEvents,
  websiteCount,
  isLoading,
}) => {
  const shouldShowTimeline = processedEvents.length > 0;
  const shouldDisplayDirectly = 
    agent === "interactive_planner_agent" || 
    (agent === "report_composer_with_citations" && finalReportWithCitations);

  if (shouldDisplayDirectly) {
    return (
      <div style={{ position: 'relative', width: '100%' }}>
        {shouldShowTimeline && agent === "interactive_planner_agent" && (
          <div style={{ width: '100%', marginBottom: '0.5rem' }}>
            <ActivityTimeline 
              processedEvents={processedEvents}
              isLoading={isLoading}
              websiteCount={websiteCount}
            />
          </div>
        )}
        
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
          <div style={{
            flex: 1,
            background: THEME.bgSecondary,
            border: `1px solid ${THEME.borderSubtle}`,
            borderRadius: '8px',
            padding: '1.25rem',
            color: THEME.textSecondary,
            position: 'relative'
          }}>
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
            <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm, remarkBreaks]}>
              {message.content}
            </ReactMarkdown>
          </div>

          <button
            onClick={() => handleCopy(message.content, message.id)}
            style={{
              padding: '0.5rem',
              background: THEME.bgCard,
              border: `1px solid ${THEME.borderSubtle}`,
              borderRadius: '4px',
              cursor: 'pointer',
              transition: 'all 0.3s ease'
            }}
          >
            {copiedMessageId === message.id ? (
              <CopyCheck style={{ width: '1rem', height: '1rem', color: THEME.green }} />
            ) : (
              <Copy style={{ width: '1rem', height: '1rem', color: THEME.textMuted }} />
            )}
          </button>
        </div>
      </div>
    );
  } 
  
  else if (shouldShowTimeline) {
    return (
      <div style={{ position: 'relative', width: '100%' }}>
        <div style={{ width: '100%' }}>
          <ActivityTimeline 
            processedEvents={processedEvents}
            isLoading={isLoading}
            websiteCount={websiteCount}
          />
        </div>
        
        {message.content && message.content.trim() && agent !== "interactive_planner_agent" && (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', marginTop: '0.5rem' }}>
            <div style={{
              flex: 1,
              background: THEME.bgSecondary,
              border: `1px solid ${THEME.borderSubtle}`,
              borderRadius: '8px',
              padding: '1.25rem',
              color: THEME.textSecondary
            }}>
              <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm, remarkBreaks]}>
                {message.content}
              </ReactMarkdown>
            </div>
            <button
              onClick={() => handleCopy(message.content, message.id)}
              style={{
                padding: '0.5rem',
                background: THEME.bgCard,
                border: `1px solid ${THEME.borderSubtle}`,
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              {copiedMessageId === message.id ? (
                <CopyCheck style={{ width: '1rem', height: '1rem', color: THEME.green }} />
              ) : (
                <Copy style={{ width: '1rem', height: '1rem', color: THEME.textMuted }} />
              )}
            </button>
          </div>
        )}
      </div>
    );
  } 
  
  else {
    return (
      <div style={{ position: 'relative', width: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
          <div style={{ flex: 1 }}>
            <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm, remarkBreaks]}>
              {message.content}
            </ReactMarkdown>
          </div>
          <button
            onClick={() => handleCopy(message.content, message.id)}
            style={{
              padding: '0.5rem',
              background: THEME.bgCard,
              border: `1px solid ${THEME.borderSubtle}`,
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            {copiedMessageId === message.id ? (
              <CopyCheck style={{ width: '1rem', height: '1rem', color: THEME.green }} />
            ) : (
              <Copy style={{ width: '1rem', height: '1rem', color: THEME.textMuted }} />
            )}
          </button>
        </div>
      </div>
    );
  }
};

// ============================================================================
// MAIN CHAT MESSAGES VIEW COMPONENT - TECH THEME
// ============================================================================
interface ChatMessagesViewProps {
  messages: { 
    type: "human" | "ai"; 
    content: string; 
    id: string; 
    agent?: string;
    finalReportWithCitations?: boolean;
  }[];
  isLoading: boolean;
  scrollAreaRef: React.RefObject<HTMLDivElement | null>;
  onSubmit: (query: string, files?: File[]) => void;
  onCancel: () => void;
  displayData: string | null;
  messageEvents: Map<string, ProcessedEvent[]>;
  websiteCount: number;
}

export function ChatMessagesView({
  messages,
  isLoading,
  scrollAreaRef,
  onSubmit,
  onCancel,
  messageEvents,
  websiteCount,
}: ChatMessagesViewProps) {
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [highlightsByMessage, setHighlightsByMessage] = useState<Record<string, string[]>>({});
  const [summaryByMessage, setSummaryByMessage] = useState<Record<string, string>>({});
  const [expandedInsights, setExpandedInsights] = useState<Record<string, boolean>>({});
  const [expandedSummary, setExpandedSummary] = useState<Record<string, boolean>>({});
  const [pinnedMessages, setPinnedMessages] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('epc-pinned-messages');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [messageTagsMap, setMessageTagsMap] = useState<Record<string, string>>(() => {
    try {
      const saved = localStorage.getItem('epc-message-tags');
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });
  const [showSessionSummary, setShowSessionSummary] = useState(false);
  const [cleanViewMessage, setCleanViewMessage] = useState<string | null>(null);
  const [openTagDropdown, setOpenTagDropdown] = useState<string | null>(null);

  // Settings State - Tech Theme
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    glowIntensity: 1,
    animationSpeed: 1,
    particleDensity: 4,
    brightness: 1,
    effectsEnabled: true,
    focusMode: false,
  });

   // Agent profiles - maps ADK agent identifiers to display info
  const agentProfiles: Record<string, { name: string; image: string; color: string }> = {
    // =========================================================================
    // NEXUS - Chief AI Agent / Root Orchestrator
    // =========================================================================
    'nexus': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'Nexus': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'nexus_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'Nexus_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    // Orchestrator patterns
    'root_orchestrator_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'root_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'orchestrator_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'orchestrator': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'main_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'coordinator_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'chief_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    // Report/Planning patterns (Nexus coordinates these)
    'report_composer_with_citations': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'report_composer': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'final_report_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'interactive_planner_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'planner_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },
    'planning_agent': { name: 'Nexus', image: NexusImg, color: THEME.cyan },

    // =========================================================================
    // ATLAS - Performance Analytics / NBOT
    // =========================================================================
    'atlas': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'Atlas': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'atlas_agent': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'Atlas_agent': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'nbot_agent': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'nbot': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'nbot_specialist': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'nbot_analysis_agent': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'performance_agent': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'analytics_agent': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'kpi_agent': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'trend_agent': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'overtime_agent': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },
    'non_billable_agent': { name: 'Atlas', image: AtlasImg, color: '#a55eea' },

    // =========================================================================
    // MAESTRO - Capacity Optimization / Scheduling
    // =========================================================================
    'maestro': { name: 'Maestro', image: MaestroImg, color: THEME.green },
    'Maestro': { name: 'Maestro', image: MaestroImg, color: THEME.green },
    'maestro_agent': { name: 'Maestro', image: MaestroImg, color: THEME.green },
    'Maestro_agent': { name: 'Maestro', image: MaestroImg, color: THEME.green },
    'schedule_agent': { name: 'Maestro', image: MaestroImg, color: THEME.green },
    'scheduling_agent': { name: 'Maestro', image: MaestroImg, color: THEME.green },
    'scheduler_agent': { name: 'Maestro', image: MaestroImg, color: THEME.green },
    'capacity_agent': { name: 'Maestro', image: MaestroImg, color: THEME.green },
    'fte_agent': { name: 'Maestro', image: MaestroImg, color: THEME.green },
    'optimization_agent': { name: 'Maestro', image: MaestroImg, color: THEME.green },
    'shift_agent': { name: 'Maestro', image: MaestroImg, color: THEME.green },
    'schedule_optimization_agent': { name: 'Maestro', image: MaestroImg, color: THEME.green },

    // =========================================================================
    // PULSE - Communications Intelligence
    // =========================================================================
    'pulse': { name: 'Pulse', image: PulseImg, color: '#a55eea' },
    'Pulse': { name: 'Pulse', image: PulseImg, color: '#a55eea' },
    'pulse_agent': { name: 'Pulse', image: PulseImg, color: '#a55eea' },
    'Pulse_agent': { name: 'Pulse', image: PulseImg, color: '#a55eea' },
    'comms_agent': { name: 'Pulse', image: PulseImg, color: '#a55eea' },
    'communication_agent': { name: 'Pulse', image: PulseImg, color: '#a55eea' },
    'communications_agent': { name: 'Pulse', image: PulseImg, color: '#a55eea' },
    'email_agent': { name: 'Pulse', image: PulseImg, color: '#a55eea' },
    'sms_agent': { name: 'Pulse', image: PulseImg, color: '#a55eea' },
    'escalation_agent': { name: 'Pulse', image: PulseImg, color: '#a55eea' },

    // =========================================================================
    // AEGIS - Compliance / Training
    // =========================================================================
    'aegis': { name: 'Aegis', image: AegisImg, color: THEME.amber },
    'Aegis': { name: 'Aegis', image: AegisImg, color: THEME.amber },
    'aegis_agent': { name: 'Aegis', image: AegisImg, color: THEME.amber },
    'Aegis_agent': { name: 'Aegis', image: AegisImg, color: THEME.amber },
    'training_agent': { name: 'Aegis', image: AegisImg, color: THEME.amber },
    'training_compliance_agent': { name: 'Aegis', image: AegisImg, color: THEME.amber },
    'compliance_agent': { name: 'Aegis', image: AegisImg, color: THEME.amber },
    'certification_agent': { name: 'Aegis', image: AegisImg, color: THEME.amber },
    'audit_agent': { name: 'Aegis', image: AegisImg, color: THEME.amber },
    'training_specialist': { name: 'Aegis', image: AegisImg, color: THEME.amber },

    // =========================================================================
    // SAGE - Strategic Research
    // =========================================================================
    'sage': { name: 'Sage', image: SageImg, color: '#00cec9' },
    'Sage': { name: 'Sage', image: SageImg, color: '#00cec9' },
    'sage_agent': { name: 'Sage', image: SageImg, color: '#00cec9' },
    'Sage_agent': { name: 'Sage', image: SageImg, color: '#00cec9' },
    'research_agent': { name: 'Sage', image: SageImg, color: '#00cec9' },
    'research_specialist': { name: 'Sage', image: SageImg, color: '#00cec9' },
    'strategic_agent': { name: 'Sage', image: SageImg, color: '#00cec9' },
    'intel_agent': { name: 'Sage', image: SageImg, color: '#00cec9' },
    'foresight_agent': { name: 'Sage', image: SageImg, color: '#00cec9' },
    'analyst_agent': { name: 'Sage', image: SageImg, color: '#00cec9' },

    // =========================================================================
    // LEXI - Team SME / RAG / Knowledge
    // =========================================================================
    'lexi': { name: 'Lexi', image: LexiImg, color: '#5468ff' },
    'Lexi': { name: 'Lexi', image: LexiImg, color: '#5468ff' },
    'lexi_agent': { name: 'Lexi', image: LexiImg, color: '#5468ff' },
    'Lexi_agent': { name: 'Lexi', image: LexiImg, color: '#5468ff' },
    'rag_agent': { name: 'Lexi', image: LexiImg, color: '#5468ff' },
    'knowledge_agent': { name: 'Lexi', image: LexiImg, color: '#5468ff' },
    'policy_agent': { name: 'Lexi', image: LexiImg, color: '#5468ff' },
    'sop_agent': { name: 'Lexi', image: LexiImg, color: '#5468ff' },
    'document_agent': { name: 'Lexi', image: LexiImg, color: '#5468ff' },
    'team_sme_agent': { name: 'Lexi', image: LexiImg, color: '#5468ff' },
    'team_sme': { name: 'Lexi', image: LexiImg, color: '#5468ff' },
    'sme_agent': { name: 'Lexi', image: LexiImg, color: '#5468ff' },

    // =========================================================================
    // SCOUT - Market Intelligence
    // =========================================================================
    'scout': { name: 'Scout', image: ScoutImg, color: '#0984e3' },
    'Scout': { name: 'Scout', image: ScoutImg, color: '#0984e3' },
    'scout_agent': { name: 'Scout', image: ScoutImg, color: '#0984e3' },
    'Scout_agent': { name: 'Scout', image: ScoutImg, color: '#0984e3' },
    'market_agent': { name: 'Scout', image: ScoutImg, color: '#0984e3' },
    'market_intelligence_agent': { name: 'Scout', image: ScoutImg, color: '#0984e3' },
    'demand_agent': { name: 'Scout', image: ScoutImg, color: '#0984e3' },
    'seasonality_agent': { name: 'Scout', image: ScoutImg, color: '#0984e3' },
    'market_trend_agent': { name: 'Scout', image: ScoutImg, color: '#0984e3' },
    'external_agent': { name: 'Scout', image: ScoutImg, color: '#0984e3' },

    // =========================================================================
    // GEARS - Workflow Automation
    // =========================================================================
    'gears': { name: 'Gears', image: GearsImg, color: '#2ed573' },
    'Gears': { name: 'Gears', image: GearsImg, color: '#2ed573' },
    'gears_agent': { name: 'Gears', image: GearsImg, color: '#2ed573' },
    'Gears_agent': { name: 'Gears', image: GearsImg, color: '#2ed573' },
    'workflow_agent': { name: 'Gears', image: GearsImg, color: '#2ed573' },
    'automation_agent': { name: 'Gears', image: GearsImg, color: '#2ed573' },
    'task_agent': { name: 'Gears', image: GearsImg, color: '#2ed573' },
    'integration_agent': { name: 'Gears', image: GearsImg, color: '#2ed573' },
    'scheduled_task_agent': { name: 'Gears', image: GearsImg, color: '#2ed573' },

    // =========================================================================
    // SENTINEL - Real-Time Monitoring & Alerts
    // =========================================================================
    'sentinel': { name: 'Sentinel', image: SentinelImg, color: '#ff6348' },
    'Sentinel': { name: 'Sentinel', image: SentinelImg, color: '#ff6348' },
    'sentinel_agent': { name: 'Sentinel', image: SentinelImg, color: '#ff6348' },
    'Sentinel_agent': { name: 'Sentinel', image: SentinelImg, color: '#ff6348' },
    'monitoring_agent': { name: 'Sentinel', image: SentinelImg, color: '#ff6348' },
    'alerts_agent': { name: 'Sentinel', image: SentinelImg, color: '#ff6348' },
    'alert_agent': { name: 'Sentinel', image: SentinelImg, color: '#ff6348' },
    'anomaly_agent': { name: 'Sentinel', image: SentinelImg, color: '#ff6348' },
    'threshold_agent': { name: 'Sentinel', image: SentinelImg, color: '#ff6348' },
    'watchlist_agent': { name: 'Sentinel', image: SentinelImg, color: '#ff6348' },
    'sla_agent': { name: 'Sentinel', image: SentinelImg, color: '#ff6348' },

    // =========================================================================
    // GENERIC FALLBACKS
    // =========================================================================
    'ace_agent': { name: 'ACE Agent', image: NexusImg, color: THEME.cyan },
    'ACE_agent': { name: 'ACE Agent', image: NexusImg, color: THEME.cyan },
    'epc_agent': { name: 'ACE Agent', image: NexusImg, color: THEME.cyan },
    'EPC Agent': { name: 'ACE Agent', image: NexusImg, color: THEME.cyan },
    'default': { name: 'ACE Agent', image: NexusImg, color: THEME.cyan },
  };

  // ============================================================================
  // HANDLER FUNCTIONS
  // ============================================================================
  
  const decodeHtmlEntities = (text: string): string => {
    try {
      const textarea = document.createElement('textarea');
      textarea.innerHTML = text;
      return textarea.value;
    } catch (err) {
      return text;
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      setSelectedFiles(Array.from(files));
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleClearFiles = () => {
    setSelectedFiles([]);
  };

  const handleCopy = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error("Failed to copy text:", err);
    }
  };

  const handleCopyMarkdown = async (content: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(content || "");
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error("Failed to copy markdown:", err);
    }
  };

  const handleCopyPlainText = async (content: string, messageId: string) => {
    try {
      const text = (content || "")
        .replace(/```[\s\S]*?```/g, "")
        .replace(/`([^`]+)`/g, "$1")
        .replace(/^[#>\-\*\+]+\s+/gm, "")
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1")
        .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, "$1")
        .replace(/\n{3,}/g, "\n\n")
        .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, "")
        .trim();

      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error("Failed to copy plain text:", err);
    }
  };

  const handleDownloadHtml = (content: string, messageId: string) => {
    try {
      const decodedContent = decodeHtmlEntities(content || "");
      
      const markdownToHtml = (markdown: string): string => {
        let html = markdown;
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
        html = html.replace(/__(.*?)__/gim, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');
        html = html.replace(/_(.*?)_/gim, '<em>$1</em>');
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        html = html.replace(/```([a-z]*)\n([\s\S]*?)```/gim, '<pre><code class="language-$1">$2</code></pre>');
        html = html.replace(/`([^`]+)`/gim, '<code>$1</code>');
        html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
        html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        html = html.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');
        html = html.replace(/^---$/gim, '<hr>');
        html = html.replace(/\n\n/gim, '</p><p>');
        html = '<p>' + html + '</p>';
        html = html.replace(/<p><\/p>/gim, '');
        return html;
      };

      const htmlContent = markdownToHtml(decodedContent);

      const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>EPC Intelligence Response</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Orbitron:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #0a0f1a;
      color: #ffffff;
      padding: 40px 20px;
      line-height: 1.7;
      min-height: 100vh;
    }
    body::before {
      content: '';
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: 
        radial-gradient(circle at 20% 80%, rgba(0, 212, 255, 0.08) 0%, transparent 50%),
        radial-gradient(circle at 80% 20%, rgba(0, 212, 255, 0.06) 0%, transparent 50%);
      pointer-events: none;
      z-index: 0;
    }
    .container {
      max-width: 900px;
      margin: 0 auto;
      background: rgba(10, 15, 26, 0.8);
      border-radius: 8px;
      border: 1px solid rgba(0, 212, 255, 0.2);
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 40px rgba(0, 212, 255, 0.1);
      overflow: hidden;
      position: relative;
      z-index: 1;
    }
    .header {
      position: relative;
      background: linear-gradient(135deg, #0a0f1a 0%, #0d1525 50%, #0a0f1a 100%);
      padding: 40px 32px;
      text-align: center;
      border-bottom: 1px solid rgba(0, 212, 255, 0.2);
    }
    .header::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 2px;
      background: linear-gradient(90deg, transparent, #00d4ff, transparent);
      box-shadow: 0 0 30px rgba(0, 212, 255, 0.5);
    }
    .header h1 {
      font-family: 'Orbitron', 'Inter', sans-serif;
      font-size: 2rem;
      font-weight: 900;
      color: #ffffff;
      text-shadow: 0 0 10px rgba(255,255,255,0.5), 0 0 30px rgba(0, 212, 255, 0.5);
      letter-spacing: 2px;
      margin-bottom: 8px;
    }
    .header p {
      font-size: 0.75rem;
      color: rgba(0, 212, 255, 0.7);
      text-transform: uppercase;
      letter-spacing: 3px;
    }
    .content {
      padding: 40px;
    }
    .content h1 {
      font-family: 'Orbitron', 'Inter', sans-serif;
      font-size: 1.75rem;
      font-weight: 700;
      color: #ffffff;
      margin: 32px 0 16px 0;
      padding-bottom: 12px;
      border-bottom: 2px solid #00d4ff;
      text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
    }
    .content h2 {
      font-family: 'Orbitron', 'Inter', sans-serif;
      font-size: 1.4rem;
      font-weight: 600;
      color: rgba(255,255,255,0.9);
      margin: 28px 0 14px 0;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(0, 212, 255, 0.2);
    }
    .content h3 {
      font-family: 'Orbitron', 'Inter', sans-serif;
      font-size: 1.15rem;
      font-weight: 600;
      color: #00d4ff;
      margin: 24px 0 12px 0;
      text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
    }
    .content p {
      margin: 16px 0;
      color: rgba(255,255,255,0.75);
      font-size: 1rem;
      line-height: 1.8;
    }
    .content ul, .content ol {
      margin: 16px 0;
      padding-left: 32px;
      color: rgba(255,255,255,0.75);
    }
    .content li {
      margin: 10px 0;
      line-height: 1.7;
    }
    .content li::marker {
      color: #00d4ff;
    }
    .content a {
      color: #00d4ff;
      text-decoration: none;
      border-bottom: 1px solid rgba(0, 212, 255, 0.3);
      transition: all 0.2s;
    }
    .content a:hover {
      background: rgba(0, 212, 255, 0.1);
      border-bottom-color: #00d4ff;
    }
    .content blockquote {
      margin: 20px 0;
      padding: 16px 24px;
      background: rgba(0, 212, 255, 0.05);
      border-left: 4px solid #00d4ff;
      border-radius: 0 8px 8px 0;
      color: rgba(255,255,255,0.75);
      font-style: italic;
    }
    .content code {
      background: rgba(0, 212, 255, 0.1);
      padding: 3px 8px;
      border-radius: 4px;
      font-family: "Courier New", monospace;
      font-size: 0.9rem;
      color: #ffa502;
      border: 1px solid rgba(0, 212, 255, 0.15);
    }
    .content pre {
      background: #0a0f1a;
      padding: 20px;
      border-radius: 8px;
      overflow-x: auto;
      margin: 20px 0;
      border: 1px solid rgba(0, 212, 255, 0.15);
    }
    .content pre code {
      background: none;
      padding: 0;
      border: none;
      color: rgba(255,255,255,0.7);
    }
    .content table {
      width: 100%;
      border-collapse: collapse;
      margin: 24px 0;
      background: rgba(10, 15, 26, 0.8);
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid rgba(0, 212, 255, 0.15);
    }
    .content th {
      background: rgba(0, 212, 255, 0.1);
      color: #00d4ff;
      font-weight: 700;
      padding: 14px 16px;
      text-align: left;
      border-bottom: 2px solid #00d4ff;
      font-size: 0.8rem;
      letter-spacing: 1px;
      text-transform: uppercase;
    }
    .content td {
      padding: 12px 16px;
      border-bottom: 1px solid rgba(0, 212, 255, 0.1);
      color: rgba(255,255,255,0.75);
    }
    .content tr:hover {
      background: rgba(0, 212, 255, 0.05);
    }
    .content hr {
      border: none;
      border-top: 1px solid rgba(0, 212, 255, 0.2);
      margin: 32px 0;
    }
    .content strong {
      color: #ffffff;
      font-weight: 600;
    }
    .footer {
      padding: 24px 40px;
      background: rgba(0, 212, 255, 0.03);
      border-top: 1px solid rgba(0, 212, 255, 0.1);
      text-align: center;
      color: rgba(0, 212, 255, 0.5);
      font-size: 0.8rem;
      letter-spacing: 1px;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>ACE Intelligence</h1>
      <p>Agentic Cognitive Enterprice</p>
    </div>
    <div class="content">
      ${htmlContent}
    </div>
    <div class="footer">
      Generated by ACE Intelligence on ${new Date().toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })}
    </div>
  </div>
</body>
</html>`;

      const blob = new Blob([html], { type: "text/html;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const shortId = (messageId || "response").slice(0, 8);
      link.href = url;
      link.download = `epc-response-${shortId}.html`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download HTML response:", err);
    }
  };

  const handleDownloadPdf = (content: string, messageId: string) => {
    try {
      const safeContent = (content || "")
        .normalize('NFC')
        .replace(/[\u{1F300}-\u{1FAFF}]/gu, '')
        .trim();
      
      const doc = new jsPDF({ unit: "pt", format: "a4", compress: true });
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      const margin = 50;
      const maxWidth = pageWidth - margin * 2;
      let cursorY = margin;
      const lineHeight = 16;

      const cleanText = (text: string): string => {
        let cleaned = text;
        cleaned = cleaned.replace(/\[([^\]]+)\]\(https?:\/\/[^\)]+\)/g, '');
        cleaned = cleaned.replace(/https?:\/\/\S+/g, '');
        cleaned = cleaned.replace(/\*\*(.*?)\*\*/g, '$1');
        cleaned = cleaned.replace(/__(.*?)__/g, '$1');
        cleaned = cleaned.replace(/\*(.*?)\*/g, '$1');
        cleaned = cleaned.replace(/_(.*?)_/g, '$1');
        cleaned = cleaned.replace(/`([^`]+)`/g, '$1');
        cleaned = cleaned.replace(/\[\]/g, '');
        cleaned = cleaned.replace(/\(\)/g, '');
        cleaned = cleaned.replace(/\s+/g, ' ');
        cleaned = cleaned.trim();
        return cleaned;
      };

      // Header
      doc.setFillColor(0, 212, 255);
      doc.rect(0, 0, pageWidth, 80, 'F');
      doc.setTextColor(10, 15, 26);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(24);
      doc.text("ACE Intelligence", pageWidth / 2, 35, { align: 'center' });
      doc.setFontSize(12);
      doc.setFont("helvetica", "normal");
      doc.text("Agentic Cognitive Enterprice - AI Agent Response", pageWidth / 2, 55, { align: 'center' });
      
      cursorY = 110;

      const lines = safeContent.split('\n');
      
      for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        if (!line) {
          cursorY += 12;
          continue;
        }

        // Headers
        if (line.startsWith('# ')) {
          if (cursorY > 130) cursorY += 30;
          doc.setFont("helvetica", "bold");
          doc.setFontSize(18);
          doc.setTextColor(10, 15, 26);
          line = cleanText(line.substring(2));
          
          const headerLines = doc.splitTextToSize(line, maxWidth);
          headerLines.forEach((headerLine: string) => {
            if (cursorY > pageHeight - margin - 40) {
              doc.addPage();
              cursorY = margin;
            }
            doc.text(headerLine, margin, cursorY);
            cursorY += 22;
          });
          doc.setLineWidth(2);
          doc.setDrawColor(0, 212, 255);
          doc.line(margin, cursorY + 2, pageWidth - margin, cursorY + 2);
          cursorY += 25;
          continue;
        }

        if (line.startsWith('## ')) {
          if (cursorY > 130) cursorY += 24;
          doc.setFont("helvetica", "bold");
          doc.setFontSize(14);
          doc.setTextColor(51, 65, 85);
          line = cleanText(line.substring(3));
          
          const headerLines = doc.splitTextToSize(line, maxWidth);
          headerLines.forEach((headerLine: string) => {
            if (cursorY > pageHeight - margin - 40) {
              doc.addPage();
              cursorY = margin;
            }
            doc.text(headerLine, margin, cursorY);
            cursorY += 18;
          });
          doc.setLineWidth(0.5);
          doc.setDrawColor(148, 163, 184);
          doc.line(margin, cursorY + 2, pageWidth - margin, cursorY + 2);
          cursorY += 20;
          continue;
        }

        if (line.startsWith('### ')) {
          if (cursorY > 130) cursorY += 18;
          doc.setFont("helvetica", "bold");
          doc.setFontSize(12);
          doc.setTextColor(0, 212, 255);
          line = cleanText(line.substring(4));
          
          const headerLines = doc.splitTextToSize(line, maxWidth);
          headerLines.forEach((headerLine: string) => {
            if (cursorY > pageHeight - margin - 40) {
              doc.addPage();
              cursorY = margin;
            }
            doc.text(headerLine, margin, cursorY);
            cursorY += 16;
          });
          cursorY += 16;
          continue;
        }

        // Bullet lists
        if (line.match(/^[\*\-\•] /)) {
          doc.setFont("helvetica", "normal");
          doc.setFontSize(10);
          doc.setTextColor(55, 65, 81);
          line = cleanText(line.substring(2));
          
          doc.setFillColor(0, 212, 255);
          doc.circle(margin + 5, cursorY - 3, 2.5, 'F');
          
          const listLines = doc.splitTextToSize(line, maxWidth - 25);
          listLines.forEach((listLine: string) => {
            if (cursorY > pageHeight - margin - 30) {
              doc.addPage();
              cursorY = margin;
            }
            doc.text(listLine, margin + 20, cursorY);
            cursorY += lineHeight;
          });
          cursorY += 8;
          continue;
        }

        // Numbered lists
        if (line.match(/^\d+\. /)) {
          doc.setFont("helvetica", "normal");
          doc.setFontSize(10);
          doc.setTextColor(55, 65, 81);
          
          const match = line.match(/^(\d+)\. (.*)$/);
          if (match) {
            const number = match[1];
            line = cleanText(match[2]);
            
            doc.setTextColor(0, 212, 255);
            doc.setFont("helvetica", "bold");
            doc.text(number + ".", margin + 2, cursorY);
            
            doc.setTextColor(55, 65, 81);
            doc.setFont("helvetica", "normal");
            const listLines = doc.splitTextToSize(line, maxWidth - 28);
            listLines.forEach((listLine: string) => {
              if (cursorY > pageHeight - margin - 30) {
                doc.addPage();
                cursorY = margin;
              }
              doc.text(listLine, margin + 25, cursorY);
              cursorY += lineHeight;
            });
            cursorY += 8;
          }
          continue;
        }

        // Regular paragraphs
        doc.setFont("helvetica", "normal");
        doc.setFontSize(10);
        doc.setTextColor(55, 65, 81);
        
        line = cleanText(line);
        
        if (!line || line.length < 3) {
          continue;
        }
        
        const textLines = doc.splitTextToSize(line, maxWidth);
        textLines.forEach((textLine: string) => {
          if (cursorY > pageHeight - margin - 30) {
            doc.addPage();
            cursorY = margin;
          }
          doc.text(textLine, margin, cursorY);
          cursorY += lineHeight;
        });
        cursorY += 10;
      }

      // Footer
      const totalPages = doc.internal.pages.length - 1;
      for (let i = 1; i <= totalPages; i++) {
        doc.setPage(i);
        doc.setFontSize(9);
        doc.setTextColor(100, 116, 139);
        doc.setFont("helvetica", "normal");
        
        const footerText = `Generated by ACE Intelligence on ${new Date().toLocaleDateString('en-US', { 
          year: 'numeric', 
          month: 'long', 
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        })} • Page ${i} of ${totalPages}`;
        
        doc.text(footerText, pageWidth / 2, pageHeight - 20, { align: 'center' });
      }

      const shortId = (messageId || "response").slice(0, 8);
      doc.save(`epc-response-${shortId}.pdf`);
    } catch (err) {
      console.error("Failed to download PDF response:", err);
    }
  };

  const handleDownloadTxt = (content: string, messageId: string) => {
    try {
      const blob = new Blob([content || ""], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const shortId = (messageId || "response").slice(0, 8);
      link.href = url;
      link.download = `epc-response-${shortId}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download TXT response:", err);
    }
  };

  const handleGenerateHighlights = (content: string, messageId: string) => {
    const raw = content || "";
    const cleaned = raw
      .replace(/```[\s\S]*?```/g, " ")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/^[#>\-\*\+]+\s+/gm, "")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1")
      .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, "$1")
      .replace(/\s+/g, " ")
      .trim();

    if (!cleaned) return;

    const sentences = cleaned
      .split(/(?<=[\.!\?])\s+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    const scored = sentences
      .map((s) => ({ text: s, score: Math.min(s.length, 300) }))
      .sort((a, b) => b.score - a.score);

    const top = scored.slice(0, 5).map((s) => s.text);

    setHighlightsByMessage((prev) => ({ ...prev, [messageId]: top }));
    setExpandedInsights((prev) => ({ ...prev, [messageId]: true }));
  };

  const handleGenerateSummary = (content: string, messageId: string) => {
    const raw = content || "";
    const cleaned = raw
      .replace(/```[\s\S]*?```/g, " ")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/^[#>\-\*\+]+\s+/gm, "")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1")
      .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, "$1")
      .replace(/\s+/g, " ")
      .trim();

    if (!cleaned) return;

    const sentences = cleaned
      .split(/(?<=[\.!\?])\s+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    const summary = sentences.slice(0, 3).join(" ");

    setSummaryByMessage((prev) => ({ ...prev, [messageId]: summary }));
    setExpandedSummary((prev) => ({ ...prev, [messageId]: true }));
  };

  const handleTogglePin = (messageId: string) => {
    setPinnedMessages((prev) => {
      const updated = prev.includes(messageId)
        ? prev.filter((id) => id !== messageId)
        : [...prev, messageId];
      try {
        localStorage.setItem('epc-pinned-messages', JSON.stringify(updated));
      } catch (err) {
        console.error('Failed to save pinned messages:', err);
      }
      return updated;
    });
  };

  const handleSetTag = (messageId: string, tag: 'decision' | 'action' | 'idea') => {
    setMessageTagsMap((prev) => {
      const updated = { ...prev, [messageId]: tag };
      try {
        localStorage.setItem('epc-message-tags', JSON.stringify(updated));
      } catch (err) {
        console.error('Failed to save message tags:', err);
      }
      return updated;
    });
  };

  const handleRemoveTag = (messageId: string) => {
    setMessageTagsMap((prev) => {
      const updated = { ...prev };
      delete updated[messageId];
      try {
        localStorage.setItem('epc-message-tags', JSON.stringify(updated));
      } catch (err) {
        console.error('Failed to remove message tag:', err);
      }
      return updated;
    });
  };

  const handleScrollToMessage = (messageId: string) => {
    const element = document.getElementById(`message-${messageId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      element.classList.add('highlight-flash');
      setTimeout(() => element.classList.remove('highlight-flash'), 2000);
    }
  };

  const handleNewChat = () => {
    window.location.reload();
  };

  const lastAiMessage = messages.slice().reverse().find(m => m.type === "ai");
  const lastAiMessageId = lastAiMessage?.id;

  // ============================================================================
  // RENDER - TECH THEME
  // ============================================================================
  return (
    <div 
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        background: THEME.bgPrimary,
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        filter: `brightness(${settings.brightness})`,
        transition: 'filter 0.3s ease',
        position: 'relative'
      }}
    >
      {/* Background Effects */}
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

      {/* ===== HEADER - TECH THEME ===== */}
      <div style={{
        position: 'relative',
        borderBottom: `1px solid ${THEME.borderSubtle}`,
        overflow: 'hidden',
        background: settings.focusMode ? THEME.bgPrimary : 'linear-gradient(135deg, #0a0f1a 0%, #0d1525 50%, #0a0f1a 100%)'
      }}>
        {/* Top accent line */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '2px',
          background: `linear-gradient(90deg, transparent, ${THEME.cyan}, transparent)`,
          boxShadow: `0 0 30px ${THEME.cyanGlow}`
        }} />

        {/* Animated gradient background */}
        {!settings.focusMode && settings.effectsEnabled && (
          <div style={{
            position: 'absolute',
            inset: 0,
            background: `linear-gradient(90deg, ${THEME.cyanSubtle} 0%, transparent 50%, ${THEME.cyanSubtle} 100%)`,
            backgroundSize: '200% 200%',
            animation: `gradientShift ${15 / settings.animationSpeed}s ease infinite`,
            opacity: 0.3
          }} />
        )}

        <div style={{
          maxWidth: '1400px',
          margin: '0 auto',
          padding: '1.5rem',
          position: 'relative',
          zIndex: 10
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '2rem' }}>
            
            {/* Left: Logo & Title */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              {/* Rotating ring logo */}
              <div style={{
                position: 'relative',
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                background: `linear-gradient(135deg, ${THEME.cyan}, ${THEME.cyanDark})`,
                animation: settings.effectsEnabled ? `spinSlow ${8 / settings.animationSpeed}s linear infinite` : 'none',
                boxShadow: `0 0 30px ${THEME.cyanGlow}`
              }}>
                <div style={{
                  position: 'absolute',
                  inset: '6px',
                  borderRadius: '50%',
                  background: THEME.bgPrimary,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <svg style={{ width: '20px', height: '20px', color: THEME.cyan }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
              </div>

              {/* Title */}
              <div>
                <h1 style={{
                  fontFamily: "'Orbitron', 'Inter', sans-serif",
                  fontSize: '1.75rem',
                  fontWeight: 900,
                  color: THEME.textPrimary,
                  textShadow: `0 0 10px rgba(255,255,255,0.5), 0 0 30px ${THEME.cyanGlow}`,
                  letterSpacing: '2px',
                  margin: 0
                }}>
                  ACE Intelligence
                </h1>
                <p style={{
                  fontSize: '0.7rem',
                  color: THEME.cyan,
                  textTransform: 'uppercase',
                  letterSpacing: '3px',
                  margin: 0,
                  opacity: 0.8
                }}>Agentic Cognitive Enterprice</p>
              </div>
            </div>

            {/* Center: Status */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              {/* Online status */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1rem',
                borderRadius: '4px',
                background: 'rgba(46, 213, 115, 0.1)',
                border: `1px solid rgba(46, 213, 115, 0.3)`
              }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: THEME.green,
                  boxShadow: `0 0 10px ${THEME.greenGlow}`,
                  animation: settings.effectsEnabled ? 'statusPulse 2s ease-in-out infinite' : 'none'
                }} />
                <span style={{ fontSize: '0.75rem', color: THEME.green, fontWeight: 600, letterSpacing: '1px' }}>AGENTS ONLINE</span>
              </div>
              
              {/* Processing indicator */}
              {isLoading && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  background: THEME.cyanSubtle,
                  border: `1px solid ${THEME.borderMedium}`
                }}>
                  <Loader2 style={{ width: '14px', height: '14px', color: THEME.cyan, animation: 'spin 1s linear infinite' }} />
                  <span style={{ fontSize: '0.75rem', color: THEME.cyan, fontWeight: 600, letterSpacing: '1px' }}>PROCESSING</span>
                </div>
              )}
            </div>

            {/* Right: Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {/* Session Summary Button */}
              <button 
                onClick={() => setShowSessionSummary(!showSessionSummary)} 
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.625rem 1rem',
                  background: THEME.bgCard,
                  border: `1px solid ${THEME.borderMedium}`,
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  color: THEME.textPrimary,
                  fontSize: '0.85rem',
                  fontWeight: 600
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = THEME.cyan;
                  e.currentTarget.style.boxShadow = `0 0 20px ${THEME.cyanGlow}`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = THEME.borderMedium;
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <Pin style={{ width: '14px', height: '14px', color: THEME.amber }} />
                <span>Summary</span>
                {pinnedMessages.length > 0 && (
                  <span style={{
                    marginLeft: '0.25rem',
                    padding: '0.125rem 0.5rem',
                    background: 'rgba(255, 165, 2, 0.2)',
                    border: '1px solid rgba(255, 165, 2, 0.4)',
                    borderRadius: '10px',
                    fontSize: '0.7rem',
                    color: THEME.amber
                  }}>
                    {pinnedMessages.length}
                  </span>
                )}
              </button>

              {/* Focus Mode Toggle */}
              <button 
                onClick={() => setSettings({ ...settings, focusMode: !settings.focusMode })} 
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.625rem 1rem',
                  background: settings.focusMode ? 'rgba(168, 85, 234, 0.2)' : THEME.bgCard,
                  border: `1px solid ${settings.focusMode ? 'rgba(168, 85, 234, 0.5)' : THEME.borderMedium}`,
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  color: settings.focusMode ? '#a855ea' : THEME.textPrimary,
                  fontSize: '0.85rem',
                  fontWeight: 600
                }}
              >
                <svg style={{ width: '14px', height: '14px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                <span>{settings.focusMode ? 'Focus ON' : 'Focus'}</span>
              </button>

              {/* Settings Button */}
              <button 
                onClick={() => setShowSettings(!showSettings)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.625rem 1rem',
                  background: THEME.bgCard,
                  border: `1px solid ${THEME.borderMedium}`,
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  color: THEME.textPrimary,
                  fontSize: '0.85rem',
                  fontWeight: 600
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = THEME.cyan;
                  e.currentTarget.style.boxShadow = `0 0 20px ${THEME.cyanGlow}`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = THEME.borderMedium;
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <svg style={{ width: '14px', height: '14px', color: THEME.cyan, transition: 'transform 0.5s ease' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span>Settings</span>
              </button>

              {/* New Chat Button */}
              <button 
                onClick={handleNewChat}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.625rem 1.25rem',
                  background: `linear-gradient(135deg, ${THEME.cyan} 0%, ${THEME.cyanDark} 100%)`,
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  color: THEME.bgPrimary,
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  boxShadow: `0 0 20px ${THEME.cyanGlow}`
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = `0 0 30px ${THEME.cyanGlow}`;
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = `0 0 20px ${THEME.cyanGlow}`;
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <svg style={{ width: '14px', height: '14px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>New Chat</span>
              </button>
            </div>
          </div>
        </div>

        {/* Bottom scanning line */}
        <div style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: '1px',
          background: `linear-gradient(90deg, transparent, ${THEME.cyan}, transparent)`,
          opacity: 0.5,
          animation: settings.effectsEnabled ? `scanHorizontal ${4 / settings.animationSpeed}s linear infinite` : 'none'
        }} />
      </div>

      {/* ===== SETTINGS PANEL ===== */}
      <div style={{
        position: 'fixed',
        top: 0,
        right: 0,
        height: '100%',
        width: '380px',
        background: 'rgba(10, 15, 26, 0.98)',
        backdropFilter: 'blur(40px)',
        borderLeft: `1px solid ${THEME.borderSubtle}`,
        boxShadow: `-20px 0 60px rgba(0,0,0,0.5), 0 0 40px ${THEME.cyanGlow}`,
        transform: showSettings ? 'translateX(0)' : 'translateX(100%)',
        transition: 'transform 0.3s ease',
        zIndex: 150,
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Panel Header */}
        <div style={{
          padding: '1.5rem',
          borderBottom: `1px solid ${THEME.borderSubtle}`,
          background: `linear-gradient(90deg, ${THEME.cyanSubtle} 0%, transparent 100%)`,
          position: 'relative'
        }}>
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '2px',
            background: `linear-gradient(90deg, ${THEME.cyan}, transparent)`,
            boxShadow: `0 0 20px ${THEME.cyanGlow}`
          }} />
          
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '8px',
                background: `linear-gradient(135deg, ${THEME.cyan}, ${THEME.cyanDark})`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: `0 0 20px ${THEME.cyanGlow}`
              }}>
                <svg style={{ width: '20px', height: '20px', color: THEME.bgPrimary }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h2 style={{ 
                fontFamily: "'Orbitron', 'Inter', sans-serif",
                fontSize: '1.125rem', 
                fontWeight: 700, 
                color: THEME.textPrimary, 
                margin: 0,
                textShadow: `0 0 15px ${THEME.cyanGlow}`,
                letterSpacing: '1px'
              }}>SETTINGS</h2>
            </div>
            <button
              onClick={() => setShowSettings(false)}
              style={{
                padding: '0.5rem',
                background: 'transparent',
                border: `1px solid ${THEME.borderSubtle}`,
                borderRadius: '4px',
                cursor: 'pointer',
                transition: 'all 0.3s ease'
              }}
            >
              <svg style={{ width: '18px', height: '18px', color: THEME.cyan }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p style={{ fontSize: '0.7rem', color: THEME.cyan, marginTop: '0.5rem', textTransform: 'uppercase', letterSpacing: '1.5px', opacity: 0.7 }}>Customize your experience</p>
        </div>

        {/* Settings Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Glow Intensity */}
          <div style={{ padding: '1.25rem', background: THEME.bgCard, borderRadius: '8px', border: `1px solid ${THEME.borderSubtle}` }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', fontSize: '0.8rem', fontWeight: 600, color: THEME.textPrimary, marginBottom: '0.875rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: THEME.cyan, boxShadow: `0 0 10px ${THEME.cyan}`, animation: 'statusPulse 2s ease-in-out infinite' }} />
              Glow Intensity: {Math.round(settings.glowIntensity * 100)}%
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={settings.glowIntensity}
              onChange={(e) => setSettings({ ...settings, glowIntensity: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: THEME.cyan, height: '4px', borderRadius: '2px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: THEME.textMuted, marginTop: '0.375rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
              <span>Off</span>
              <span>Normal</span>
              <span>Intense</span>
            </div>
          </div>

          {/* Animation Speed */}
          <div style={{ padding: '1.25rem', background: THEME.bgCard, borderRadius: '8px', border: `1px solid ${THEME.borderSubtle}` }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', fontSize: '0.8rem', fontWeight: 600, color: THEME.textPrimary, marginBottom: '0.875rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: THEME.green, boxShadow: `0 0 10px ${THEME.green}`, animation: 'statusPulse 2s ease-in-out infinite' }} />
              Animation Speed: {settings.animationSpeed}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={settings.animationSpeed}
              onChange={(e) => setSettings({ ...settings, animationSpeed: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: THEME.green, height: '4px', borderRadius: '2px' }}
            />
          </div>

          {/* Particle Density */}
          <div style={{ padding: '1.25rem', background: THEME.bgCard, borderRadius: '8px', border: `1px solid ${THEME.borderSubtle}` }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', fontSize: '0.8rem', fontWeight: 600, color: THEME.textPrimary, marginBottom: '0.875rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#a55eea', boxShadow: '0 0 10px #a55eea', animation: 'statusPulse 2s ease-in-out infinite' }} />
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
          <div style={{ padding: '1.25rem', background: THEME.bgCard, borderRadius: '8px', border: `1px solid ${THEME.borderSubtle}` }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', fontSize: '0.8rem', fontWeight: 600, color: THEME.textPrimary, marginBottom: '0.875rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: THEME.amber, boxShadow: `0 0 10px ${THEME.amber}`, animation: 'statusPulse 2s ease-in-out infinite' }} />
              Brightness: {Math.round(settings.brightness * 100)}%
            </label>
            <input
              type="range"
              min="0.5"
              max="1.5"
              step="0.1"
              value={settings.brightness}
              onChange={(e) => setSettings({ ...settings, brightness: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: THEME.amber, height: '4px', borderRadius: '2px' }}
            />
          </div>

          {/* Effects Toggle */}
          <div
            onClick={() => setSettings({ ...settings, effectsEnabled: !settings.effectsEnabled })}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '1.25rem',
              background: THEME.bgCard,
              borderRadius: '8px',
              border: `1px solid ${THEME.borderSubtle}`,
              cursor: 'pointer',
              transition: 'all 0.3s ease'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{ fontSize: '1.25rem' }}>⚡</span>
              <div>
                <p style={{ fontSize: '0.8rem', fontWeight: 600, color: THEME.textPrimary, margin: 0, textTransform: 'uppercase', letterSpacing: '1px' }}>Enable Effects</p>
                <p style={{ fontSize: '0.65rem', color: THEME.textMuted, margin: 0, marginTop: '0.25rem' }}>Animations & Glows</p>
              </div>
            </div>
            <div style={{
              width: '48px',
              height: '26px',
              borderRadius: '13px',
              background: settings.effectsEnabled ? THEME.cyan : 'rgba(255,255,255,0.2)',
              boxShadow: settings.effectsEnabled ? `0 0 15px ${THEME.cyanGlow}` : 'none',
              transition: 'all 0.3s ease',
              position: 'relative'
            }}>
              <div style={{
                width: '22px',
                height: '22px',
                borderRadius: '50%',
                background: settings.effectsEnabled ? THEME.bgPrimary : '#fff',
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
              focusMode: false,
            })}
            style={{
              width: '100%',
              padding: '1rem',
              background: 'rgba(255, 71, 87, 0.1)',
              border: `1px solid rgba(255, 71, 87, 0.3)`,
              borderRadius: '4px',
              color: THEME.red,
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.625rem',
              transition: 'all 0.3s ease',
              textTransform: 'uppercase',
              letterSpacing: '1px'
            }}
          >
            <svg style={{ width: '16px', height: '16px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Reset Defaults
          </button>
        </div>

        {/* Panel Footer */}
        <div style={{
          padding: '1rem',
          borderTop: `1px solid ${THEME.borderSubtle}`,
          background: THEME.bgCard,
          textAlign: 'center'
        }}>
          <p style={{ 
            fontFamily: "'Orbitron', 'Inter', sans-serif",
            fontSize: '0.65rem', 
            color: THEME.cyan, 
            margin: 0,
            letterSpacing: '2px',
            opacity: 0.5
          }}>EPC INTELLIGENCE v1.0</p>
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

      {/* ===== SESSION SUMMARY SIDEBAR ===== */}
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        height: '100%',
        width: '380px',
        background: 'rgba(10, 15, 26, 0.98)',
        backdropFilter: 'blur(40px)',
        borderRight: `1px solid ${THEME.borderSubtle}`,
        boxShadow: `20px 0 60px rgba(0,0,0,0.5), 0 0 40px ${THEME.amberGlow}`,
        transform: showSessionSummary ? 'translateX(0)' : 'translateX(-100%)',
        transition: 'transform 0.3s ease',
        zIndex: 150,
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Sidebar Header */}
        <div style={{
          padding: '1.5rem',
          borderBottom: `1px solid ${THEME.borderSubtle}`,
          background: `linear-gradient(90deg, rgba(255, 165, 2, 0.1) 0%, transparent 100%)`,
          position: 'relative'
        }}>
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '2px',
            background: `linear-gradient(90deg, ${THEME.amber}, transparent)`,
            boxShadow: `0 0 20px ${THEME.amberGlow}`
          }} />
          
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Pin style={{ width: '20px', height: '20px', color: THEME.amber }} />
              <h2 style={{ 
                fontFamily: "'Orbitron', 'Inter', sans-serif",
                fontSize: '1.125rem', 
                fontWeight: 700, 
                color: THEME.textPrimary, 
                margin: 0,
                letterSpacing: '1px'
              }}>Session Summary</h2>
            </div>
            <button
              onClick={() => setShowSessionSummary(false)}
              style={{
                padding: '0.5rem',
                background: 'transparent',
                border: `1px solid ${THEME.borderSubtle}`,
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              <svg style={{ width: '18px', height: '18px', color: THEME.amber }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p style={{ fontSize: '0.7rem', color: THEME.amber, marginTop: '0.5rem', opacity: 0.7 }}>Pinned insights from this conversation</p>
        </div>

        {/* Pinned Messages List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
          {pinnedMessages.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center', padding: '1.5rem' }}>
              <Pin style={{ width: '48px', height: '48px', color: THEME.textMuted, marginBottom: '0.75rem' }} />
              <p style={{ fontSize: '0.9rem', color: THEME.textMuted, marginBottom: '0.5rem' }}>No pinned messages yet</p>
              <p style={{ fontSize: '0.75rem', color: THEME.textMuted, opacity: 0.7 }}>Click the Pin button on AI responses to save important insights here</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {pinnedMessages.map((msgId) => {
                const msg = messages.find(m => m.id === msgId);
                if (!msg || msg.type !== 'ai') return null;
                
                const tag = messageTagsMap[msgId];
                const snippet = msg.content.substring(0, 150) + (msg.content.length > 150 ? '...' : '');
                
                return (
                  <div 
                    key={msgId}
                    onClick={() => {
                      handleScrollToMessage(msgId);
                      setShowSessionSummary(false);
                    }}
                    style={{
                      background: THEME.bgCard,
                      border: `1px solid ${THEME.borderSubtle}`,
                      borderRadius: '8px',
                      padding: '1rem',
                      cursor: 'pointer',
                      transition: 'all 0.3s ease'
                    }}
                  >
                    {/* Tag Badge */}
                    {tag && (
                      <div style={{ marginBottom: '0.5rem' }}>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          background: tag === 'decision' ? 'rgba(46, 213, 115, 0.15)' :
                                      tag === 'action' ? 'rgba(255, 165, 2, 0.15)' :
                                      THEME.cyanSubtle,
                          color: tag === 'decision' ? THEME.green :
                                 tag === 'action' ? THEME.amber :
                                 THEME.cyan,
                          border: `1px solid ${tag === 'decision' ? 'rgba(46, 213, 115, 0.4)' :
                                               tag === 'action' ? 'rgba(255, 165, 2, 0.4)' :
                                               THEME.borderMedium}`
                        }}>
                          {tag === 'decision' ? '✅ Decision' : tag === 'action' ? '📝 Action Item' : '💡 Idea'}
                        </span>
                      </div>
                    )}
                    
                    {/* Agent Info */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                      <div style={{
                        width: '24px',
                        height: '24px',
                        borderRadius: '50%',
                        background: `linear-gradient(135deg, ${THEME.cyan}, ${THEME.cyanDark})`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        overflow: 'hidden'
                      }}>
                        {msg.agent && agentProfiles[msg.agent as keyof typeof agentProfiles] ? (
                          <img 
                            src={agentProfiles[msg.agent as keyof typeof agentProfiles].image}
                            alt={agentProfiles[msg.agent as keyof typeof agentProfiles].name}
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          />
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: THEME.bgPrimary }}>⚡</span>
                        )}
                      </div>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: THEME.textMuted }}>
                        {msg.agent && agentProfiles[msg.agent as keyof typeof agentProfiles] 
                          ? agentProfiles[msg.agent as keyof typeof agentProfiles].name 
                          : 'EPC Agent'}
                      </span>
                    </div>
                    
                    {/* Message Snippet */}
                    <p style={{ fontSize: '0.8rem', color: THEME.textSecondary, margin: 0, marginBottom: '0.75rem', lineHeight: 1.5 }}>{snippet}</p>
                    
                    {/* Action Buttons */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '0.5rem', borderTop: `1px solid ${THEME.borderSubtle}` }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleScrollToMessage(msgId);
                          setShowSessionSummary(false);
                        }}
                        style={{ fontSize: '0.75rem', color: THEME.cyan, background: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                      >
                        <svg style={{ width: '12px', height: '12px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                        Jump to message
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTogglePin(msgId);
                        }}
                        style={{ fontSize: '0.75rem', color: THEME.red, background: 'transparent', border: 'none', cursor: 'pointer' }}
                      >
                        Unpin
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Clear All Button */}
        {pinnedMessages.length > 0 && (
          <div style={{ padding: '1rem', borderTop: `1px solid ${THEME.borderSubtle}` }}>
            <button
              onClick={() => {
                setPinnedMessages([]);
                localStorage.removeItem('epc-pinned-messages');
              }}
              style={{
                width: '100%',
                padding: '0.75rem',
                background: 'rgba(255, 71, 87, 0.1)',
                border: `1px solid rgba(255, 71, 87, 0.3)`,
                borderRadius: '4px',
                color: THEME.red,
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Clear All Pins
            </button>
          </div>
        )}
      </div>

      {/* Session Summary Overlay */}
      {showSessionSummary && (
        <div 
          onClick={() => setShowSessionSummary(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(10, 15, 26, 0.5)',
            zIndex: 140
          }}
        />
      )}

      {/* ===== CLEAN VIEW MODAL ===== */}
      {cleanViewMessage && (() => {
        const msg = messages.find(m => m.id === cleanViewMessage);
        if (!msg) return null;
        
        return (
          <>
            <div 
              onClick={() => setCleanViewMessage(null)}
              style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(10, 15, 26, 0.9)',
                backdropFilter: 'blur(8px)',
                zIndex: 200
              }}
            />
            <div style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '90%',
              maxWidth: '900px',
              maxHeight: '85vh',
              background: '#ffffff',
              borderRadius: '8px',
              boxShadow: `0 25px 100px rgba(0,0,0,0.5), 0 0 60px ${THEME.cyanGlow}`,
              zIndex: 201,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden'
            }}>
              {/* Modal Header */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1.5rem',
                borderBottom: '1px solid #e2e8f0'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    background: `linear-gradient(135deg, ${THEME.cyan}, ${THEME.cyanDark})`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden'
                  }}>
                    {msg.agent && agentProfiles[msg.agent as keyof typeof agentProfiles] ? (
                      <img 
                        src={agentProfiles[msg.agent as keyof typeof agentProfiles].image}
                        alt={agentProfiles[msg.agent as keyof typeof agentProfiles].name}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    ) : (
                      <span style={{ color: THEME.bgPrimary }}>⚡</span>
                    )}
                  </div>
                  <div>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#1e293b', margin: 0 }}>Clean View</h3>
                    <p style={{ fontSize: '0.75rem', color: '#64748b', margin: 0 }}>
                      {msg.agent && agentProfiles[msg.agent as keyof typeof agentProfiles] 
                        ? agentProfiles[msg.agent as keyof typeof agentProfiles].name 
                        : 'EPC Agent'} Response
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setCleanViewMessage(null)}
                  style={{
                    padding: '0.5rem',
                    background: 'transparent',
                    border: '1px solid #e2e8f0',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  <svg style={{ width: '20px', height: '20px', color: '#64748b' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Modal Content */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '2rem', background: '#f8fafc' }}>
                {/* Highlights Section */}
                {highlightsByMessage[cleanViewMessage] && highlightsByMessage[cleanViewMessage].length > 0 && (
                  <div style={{
                    marginBottom: '1.5rem',
                    padding: '1rem 1.5rem',
                    background: 'rgba(0, 212, 255, 0.05)',
                    borderLeft: `4px solid ${THEME.cyan}`,
                    borderRadius: '0 8px 8px 0'
                  }}>
                    <h4 style={{ fontSize: '0.8rem', fontWeight: 700, color: THEME.cyanDark, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ width: '8px', height: '8px', background: THEME.cyan, borderRadius: '50%' }} />
                      KEY INSIGHTS
                    </h4>
                    <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
                      {highlightsByMessage[cleanViewMessage].map((item, idx) => (
                        <li key={idx} style={{ fontSize: '0.9rem', color: '#475569', marginBottom: '0.375rem' }}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Summary Section */}
                {summaryByMessage[cleanViewMessage] && (
                  <div style={{
                    marginBottom: '1.5rem',
                    padding: '1rem 1.5rem',
                    background: 'rgba(46, 213, 115, 0.05)',
                    borderLeft: `4px solid ${THEME.green}`,
                    borderRadius: '0 8px 8px 0'
                  }}>
                    <h4 style={{ fontSize: '0.8rem', fontWeight: 700, color: '#059669', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ width: '8px', height: '8px', background: THEME.green, borderRadius: '50%' }} />
                      EXECUTIVE SUMMARY
                    </h4>
                    <p style={{ fontSize: '0.9rem', color: '#475569', margin: 0 }}>{summaryByMessage[cleanViewMessage]}</p>
                  </div>
                )}

                {/* Main Content */}
                <div style={{ color: '#334155', fontSize: '1rem', lineHeight: 1.8 }}>
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm, remarkBreaks]}
                    components={{
                      h1: ({children}) => <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1e293b', marginTop: '1.5rem', marginBottom: '0.75rem', paddingBottom: '0.5rem', borderBottom: `2px solid ${THEME.cyan}` }}>{children}</h1>,
                      h2: ({children}) => <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#334155', marginTop: '1.25rem', marginBottom: '0.5rem' }}>{children}</h2>,
                      h3: ({children}) => <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#475569', marginTop: '1rem', marginBottom: '0.375rem' }}>{children}</h3>,
                      p: ({children}) => <p style={{ marginBottom: '0.875rem', lineHeight: 1.8 }}>{children}</p>,
                      ul: ({children}) => <ul style={{ paddingLeft: '1.5rem', marginBottom: '1rem' }}>{children}</ul>,
                      ol: ({children}) => <ol style={{ paddingLeft: '1.5rem', marginBottom: '1rem' }}>{children}</ol>,
                      li: ({children}) => <li style={{ marginBottom: '0.375rem' }}>{children}</li>,
                      code: ({children}) => <code style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px', fontSize: '0.85rem', color: '#e11d48' }}>{children}</code>,
                      pre: ({children}) => <pre style={{ background: '#1e293b', color: '#e2e8f0', padding: '1rem', borderRadius: '8px', overflowX: 'auto', margin: '1rem 0' }}>{children}</pre>,
                      a: ({children, href}) => <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: THEME.cyan, textDecoration: 'underline' }}>{children}</a>,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </div>

              {/* Modal Footer */}
              <div style={{
                padding: '1rem 1.5rem',
                borderTop: '1px solid #e2e8f0',
                background: '#ffffff',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => handleCopy(msg.content, msg.id)}
                    style={{ padding: '0.5rem 1rem', background: '#f1f5f9', border: 'none', borderRadius: '4px', fontSize: '0.85rem', color: '#475569', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.375rem' }}
                  >
                    <Copy style={{ width: '14px', height: '14px' }} />
                    Copy
                  </button>
                  <button
                    onClick={() => handleDownloadPdf(msg.content, msg.id)}
                    style={{ padding: '0.5rem 1rem', background: '#f1f5f9', border: 'none', borderRadius: '4px', fontSize: '0.85rem', color: '#475569', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.375rem' }}
                  >
                    <Download style={{ width: '14px', height: '14px' }} />
                    PDF
                  </button>
                </div>
                <button
                  onClick={() => setCleanViewMessage(null)}
                  style={{ padding: '0.5rem 1rem', background: THEME.cyan, border: 'none', borderRadius: '4px', fontSize: '0.85rem', color: THEME.bgPrimary, fontWeight: 600, cursor: 'pointer' }}
                >
                  Close
                </button>
              </div>
            </div>
          </>
        );
      })()}

      {/* ===== MESSAGES AREA ===== */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', width: '100%', overflow: 'hidden', background: THEME.bgPrimary, position: 'relative', zIndex: 1 }}>
        <ScrollArea ref={scrollAreaRef} style={{ flex: 1, width: '100%', height: '100%' }}>
          <div style={{ padding: '1.5rem', maxWidth: '1400px', margin: '0 auto' }}>
            
            {/* Map through messages */}
            {messages.map((message) => {
              const eventsForMessage = message.type === "ai" 
                ? (messageEvents.get(message.id) || []) 
                : [];
              
              const isCurrentMessageTheLastAiMessage = 
                message.type === "ai" && message.id === lastAiMessageId;

              // DEBUG: Log agent identifier to console
              if (message.type === "ai") {
                console.log('[DEBUG] Agent identifier received:', {
                  agent: message.agent,
                  agentType: typeof message.agent,
                  hasProfile: message.agent ? !!agentProfiles[message.agent as keyof typeof agentProfiles] : false,
                  allKeys: Object.keys(agentProfiles)
                });
              }

              // DEBUG: Log agent identifier to console
              if (message.type === "ai") {
                console.log('[DEBUG] Agent identifier received:', {
                  agent: message.agent,
                  agentType: typeof message.agent,
                  hasProfile: message.agent ? !!agentProfiles[message.agent as keyof typeof agentProfiles] : false,
                  allKeys: Object.keys(agentProfiles)
                });
              }

              return (
                <div
                  key={message.id}
                  id={`message-${message.id}`}
                  style={{
                    display: 'flex',
                    justifyContent: message.type === "human" ? 'flex-end' : 'flex-start',
                    marginBottom: '1.5rem'
                  }}
                >
                  {message.type === "human" ? (
                    <HumanMessageBubble message={message} mdComponents={mdComponents} />
                  ) : (
                    <div style={{
                      position: 'relative',
                      width: '100%',
                      background: THEME.bgSecondary,
                      border: `1px solid ${THEME.borderSubtle}`,
                      borderRadius: '8px',
                      padding: '1.5rem',
                      transition: 'all 0.3s ease'
                    }}>
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
                      
                      {/* Agent Header */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                        <div style={{
                          position: 'relative',
                          width: '48px',
                          height: '48px',
                          borderRadius: '50%',
                          boxShadow: `0 0 20px ${THEME.cyanGlow}`,
                          border: `2px solid ${THEME.borderMedium}`
                        }}>
                          {message.agent && agentProfiles[message.agent as keyof typeof agentProfiles] ? (
                            <img 
                              src={agentProfiles[message.agent as keyof typeof agentProfiles].image}
                              alt={agentProfiles[message.agent as keyof typeof agentProfiles].name}
                              style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }}
                            />
                          ) : (
                            <div style={{
                              width: '100%',
                              height: '100%',
                              borderRadius: '50%',
                              background: `linear-gradient(135deg, ${THEME.cyan}, ${THEME.cyanDark})`,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: THEME.bgPrimary,
                              fontSize: '1.25rem'
                            }}>
                              ⚡
                            </div>
                          )}
                        </div>
                        <div>
                          <span style={{ 
                            fontFamily: "'Orbitron', 'Inter', sans-serif",
                            fontSize: '0.9rem', 
                            fontWeight: 700, 
                            color: THEME.textPrimary,
                            textShadow: `0 0 10px ${THEME.cyanGlow}`
                          }}>
                            {message.agent && agentProfiles[message.agent as keyof typeof agentProfiles] 
                              ? agentProfiles[message.agent as keyof typeof agentProfiles].name 
                              : 'ACE Analysis'}
                          </span>
                          <span style={{ 
                            display: 'block',
                            fontSize: '0.7rem', 
                            color: THEME.cyan,
                            textTransform: 'uppercase',
                            letterSpacing: '1px'
                          }}>AI Agent</span>
                        </div>
                      </div>
                      
                      {/* Message Content */}
                      <div style={{ color: THEME.textSecondary, lineHeight: 1.8 }}>
                        <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm, remarkBreaks]}>
                          {message.content}
                        </ReactMarkdown>

                        {/* Insights Section */}
                        {highlightsByMessage[message.id] && highlightsByMessage[message.id].length > 0 && (
                          <div style={{
                            marginTop: '1rem',
                            padding: '1rem',
                            borderRadius: '8px',
                            background: THEME.cyanSubtle,
                            border: `1px solid ${THEME.borderMedium}`
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: THEME.cyan, boxShadow: `0 0 8px ${THEME.cyan}` }} />
                                <span style={{ fontSize: '0.75rem', color: THEME.cyan, fontWeight: 600, letterSpacing: '1px', textTransform: 'uppercase' }}>KEY INSIGHTS</span>
                              </div>
                              <button
                                onClick={() => setExpandedInsights((prev) => ({ ...prev, [message.id]: !prev[message.id] }))}
                                style={{ fontSize: '0.65rem', color: THEME.cyan, background: 'transparent', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
                              >
                                {expandedInsights[message.id] ? "Hide" : "Show"}
                              </button>
                            </div>
                            {expandedInsights[message.id] && (
                              <ul style={{ listStyleType: 'disc', paddingLeft: '1.25rem', margin: 0 }}>
                                {highlightsByMessage[message.id].map((item, idx) => (
                                  <li key={idx} style={{ color: THEME.textSecondary, fontSize: '0.85rem', marginBottom: '0.375rem' }}>{item}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        )}

                        {/* Summary Section */}
                        {summaryByMessage[message.id] && (
                          <div style={{
                            marginTop: '0.75rem',
                            padding: '1rem',
                            borderRadius: '8px',
                            background: 'rgba(46, 213, 115, 0.05)',
                            border: `1px solid rgba(46, 213, 115, 0.3)`
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: THEME.green, boxShadow: `0 0 8px ${THEME.green}` }} />
                                <span style={{ fontSize: '0.75rem', color: THEME.green, fontWeight: 600, letterSpacing: '1px', textTransform: 'uppercase' }}>SUMMARY</span>
                              </div>
                              <button
                                onClick={() => setExpandedSummary((prev) => ({ ...prev, [message.id]: !prev[message.id] }))}
                                style={{ fontSize: '0.65rem', color: THEME.green, background: 'transparent', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
                              >
                                {expandedSummary[message.id] ? "Hide" : "Show"}
                              </button>
                            </div>
                            {expandedSummary[message.id] && (
                              <p style={{ color: THEME.textSecondary, fontSize: '0.85rem', margin: 0 }}>{summaryByMessage[message.id]}</p>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Tag Display */}
                      {messageTagsMap[message.id] && (
                        <div style={{ marginTop: '1rem', marginBottom: '0.5rem' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.375rem 0.75rem',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            background: messageTagsMap[message.id] === 'decision' ? 'rgba(46, 213, 115, 0.15)' :
                                        messageTagsMap[message.id] === 'action' ? 'rgba(255, 165, 2, 0.15)' :
                                        THEME.cyanSubtle,
                            color: messageTagsMap[message.id] === 'decision' ? THEME.green :
                                   messageTagsMap[message.id] === 'action' ? THEME.amber :
                                   THEME.cyan,
                            border: `1px solid ${messageTagsMap[message.id] === 'decision' ? 'rgba(46, 213, 115, 0.4)' :
                                                 messageTagsMap[message.id] === 'action' ? 'rgba(255, 165, 2, 0.4)' :
                                                 THEME.borderMedium}`
                          }}>
                            {messageTagsMap[message.id] === 'decision' ? '✅ Decision' : 
                             messageTagsMap[message.id] === 'action' ? '📝 Action Item' : 
                             '💡 Idea'}
                            <button
                              onClick={() => handleRemoveTag(message.id)}
                              style={{ marginLeft: '0.25rem', background: 'transparent', border: 'none', cursor: 'pointer', color: 'inherit', opacity: 0.7 }}
                            >
                              ✕
                            </button>
                          </span>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div style={{ marginTop: '1rem', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.5rem' }}>
                        
                        {/* Pin */}
                        <button
                          onClick={() => handleTogglePin(message.id)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.375rem',
                            padding: '0.375rem 0.75rem',
                            border: `1px solid ${pinnedMessages.includes(message.id) ? 'rgba(255, 165, 2, 0.4)' : THEME.borderSubtle}`,
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            transition: 'all 0.2s ease',
                            cursor: 'pointer',
                            background: pinnedMessages.includes(message.id) ? 'rgba(255, 165, 2, 0.15)' : THEME.bgCard,
                            color: pinnedMessages.includes(message.id) ? THEME.amber : THEME.textMuted
                          }}
                        >
                          <Pin style={{ width: '12px', height: '12px' }} />
                          {pinnedMessages.includes(message.id) ? 'Pinned' : 'Pin'}
                        </button>

                        {/* Tag Dropdown */}
                        {!messageTagsMap[message.id] && (
                          <div style={{ position: 'relative' }}>
                            <button 
                              onClick={() => setOpenTagDropdown(openTagDropdown === message.id ? null : message.id)}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.375rem',
                                padding: '0.375rem 0.75rem',
                                background: THEME.bgCard,
                                border: `1px solid ${THEME.borderSubtle}`,
                                borderRadius: '4px',
                                fontSize: '0.75rem',
                                color: THEME.textMuted,
                                cursor: 'pointer',
                                transition: 'all 0.2s ease'
                              }}
                            >
                              <svg style={{ width: '12px', height: '12px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                              </svg>
                              Tag
                            </button>
                            {openTagDropdown === message.id && (
                              <div style={{
                                position: 'absolute',
                                left: 0,
                                top: '100%',
                                marginTop: '0.25rem',
                                zIndex: 10,
                                background: THEME.bgPrimary,
                                border: `1px solid ${THEME.borderMedium}`,
                                borderRadius: '4px',
                                boxShadow: `0 10px 30px rgba(0,0,0,0.5), 0 0 20px ${THEME.cyanGlow}`,
                                overflow: 'hidden'
                              }}>
                                <button 
                                  onClick={() => { handleSetTag(message.id, 'decision'); setOpenTagDropdown(null); }} 
                                  style={{ width: '100%', padding: '0.5rem 0.75rem', textAlign: 'left', fontSize: '0.75rem', background: 'transparent', border: 'none', color: THEME.green, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', whiteSpace: 'nowrap' }}
                                >
                                  ✅ Decision
                                </button>
                                <button 
                                  onClick={() => { handleSetTag(message.id, 'action'); setOpenTagDropdown(null); }} 
                                  style={{ width: '100%', padding: '0.5rem 0.75rem', textAlign: 'left', fontSize: '0.75rem', background: 'transparent', border: 'none', color: THEME.amber, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', whiteSpace: 'nowrap' }}
                                >
                                  📝 Action
                                </button>
                                <button 
                                  onClick={() => { handleSetTag(message.id, 'idea'); setOpenTagDropdown(null); }} 
                                  style={{ width: '100%', padding: '0.5rem 0.75rem', textAlign: 'left', fontSize: '0.75rem', background: 'transparent', border: 'none', color: THEME.cyan, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', whiteSpace: 'nowrap' }}
                                >
                                  💡 Idea
                                </button>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Clean View Button */}
                        <button 
                          onClick={() => setCleanViewMessage(message.id)}
                          style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.375rem 0.75rem', background: THEME.bgCard, border: `1px solid ${THEME.borderSubtle}`, borderRadius: '4px', fontSize: '0.75rem', color: THEME.textMuted, cursor: 'pointer', transition: 'all 0.2s ease' }}
                        >
                          <svg style={{ width: '12px', height: '12px' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                          Clean View
                        </button>

                        {/* Separator */}
                        <div style={{ height: '1.5rem', width: '1px', background: THEME.borderSubtle }} />

                        {/* Copy Actions */}
                        <button onClick={() => handleCopy(message.content, message.id)} style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.375rem 0.75rem', background: THEME.bgCard, border: `1px solid ${THEME.borderSubtle}`, borderRadius: '4px', fontSize: '0.75rem', color: THEME.textMuted, cursor: 'pointer', transition: 'all 0.2s ease' }}>
                          {copiedMessageId === message.id ? <CopyCheck style={{ width: '12px', height: '12px', color: THEME.green }} /> : <Copy style={{ width: '12px', height: '12px' }} />}
                          {copiedMessageId === message.id ? 'Copied!' : 'Copy'}
                        </button>

                        <button onClick={() => handleCopyMarkdown(message.content, message.id)} style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.375rem 0.75rem', background: THEME.bgCard, border: `1px solid ${THEME.borderSubtle}`, borderRadius: '4px', fontSize: '0.75rem', color: THEME.textMuted, cursor: 'pointer', transition: 'all 0.2s ease' }}>
                          <Copy style={{ width: '12px', height: '12px' }} />
                          Markdown
                        </button>

                        <button onClick={() => handleCopyPlainText(message.content, message.id)} style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.375rem 0.75rem', background: THEME.bgCard, border: `1px solid ${THEME.borderSubtle}`, borderRadius: '4px', fontSize: '0.75rem', color: THEME.textMuted, cursor: 'pointer', transition: 'all 0.2s ease' }}>
                          <Copy style={{ width: '12px', height: '12px' }} />
                          Text
                        </button>

                        {/* Separator */}
                        <div style={{ height: '1.5rem', width: '1px', background: THEME.borderSubtle }} />

                        {/* Download Actions */}
                        <button onClick={() => handleDownloadHtml(message.content, message.id)} style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.375rem 0.75rem', background: THEME.bgCard, border: `1px solid ${THEME.borderSubtle}`, borderRadius: '4px', fontSize: '0.75rem', color: THEME.textMuted, cursor: 'pointer', transition: 'all 0.2s ease' }}>
                          <Download style={{ width: '12px', height: '12px' }} />
                          HTML
                        </button>

                        <button onClick={() => handleDownloadPdf(message.content, message.id)} style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.375rem 0.75rem', background: THEME.bgCard, border: `1px solid ${THEME.borderSubtle}`, borderRadius: '4px', fontSize: '0.75rem', color: THEME.textMuted, cursor: 'pointer', transition: 'all 0.2s ease' }}>
                          <Download style={{ width: '12px', height: '12px' }} />
                          PDF
                        </button>

                        <button onClick={() => handleDownloadTxt(message.content, message.id)} style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.375rem 0.75rem', background: THEME.bgCard, border: `1px solid ${THEME.borderSubtle}`, borderRadius: '4px', fontSize: '0.75rem', color: THEME.textMuted, cursor: 'pointer', transition: 'all 0.2s ease' }}>
                          <Download style={{ width: '12px', height: '12px' }} />
                          TXT
                        </button>

                        {/* Separator */}
                        <div style={{ height: '1.5rem', width: '1px', background: THEME.borderSubtle }} />

                        {/* AI Analysis */}
                        <button onClick={() => handleGenerateHighlights(message.content, message.id)} style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.375rem 0.75rem', background: THEME.cyanSubtle, border: `1px solid ${THEME.borderMedium}`, borderRadius: '4px', fontSize: '0.75rem', color: THEME.cyan, cursor: 'pointer', transition: 'all 0.2s ease' }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: THEME.cyan, boxShadow: `0 0 6px ${THEME.cyan}` }} />
                          Highlights
                        </button>

                        <button onClick={() => handleGenerateSummary(message.content, message.id)} style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.375rem 0.75rem', background: 'rgba(46, 213, 115, 0.1)', border: '1px solid rgba(46, 213, 115, 0.3)', borderRadius: '4px', fontSize: '0.75rem', color: THEME.green, cursor: 'pointer', transition: 'all 0.2s ease' }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: THEME.green, boxShadow: `0 0 6px ${THEME.green}` }} />
                          Summary
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            
            {/* Loading Indicators */}
            {isLoading && !lastAiMessage && messages.some(m => m.type === 'human') && (
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: THEME.textMuted }}>
                  <Loader2 style={{ width: '16px', height: '16px', animation: 'spin 1s linear infinite' }} />
                  <span>Thinking...</span>
                </div>
              </div>
            )}
            
            {isLoading && messages.length > 0 && messages[messages.length - 1].type === 'human' && (
              <div style={{ display: 'flex', justifyContent: 'flex-start', paddingLeft: '2.5rem', paddingTop: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: THEME.textMuted }}>
                  <Loader2 style={{ width: '16px', height: '16px', animation: 'spin 1s linear infinite' }} />
                  <span>Thinking...</span>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
      
      {/* ===== INPUT AREA ===== */}
      <div style={{
        position: 'relative',
        borderTop: `1px solid ${THEME.borderSubtle}`,
        padding: '1rem 1.5rem',
        width: '100%',
        overflow: 'hidden',
        background: settings.focusMode ? THEME.bgPrimary : 'linear-gradient(135deg, #0a0f1a 0%, #0d1525 100%)'
      }}>
        {/* Scanning line at top */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '1px',
          background: `linear-gradient(90deg, transparent, ${THEME.cyan}, transparent)`,
          opacity: 0.5,
          animation: settings.effectsEnabled ? `scanHorizontal ${4 / settings.animationSpeed}s linear infinite` : 'none'
        }} />
        
        <div style={{ maxWidth: '1400px', margin: '0 auto', position: 'relative', zIndex: 10 }}>
          
          {/* Suggestion Chips */}
          {!isLoading && messages.length === 0 && (
            <div style={{ marginBottom: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.75rem', justifyContent: 'center' }}>
              {[
                { icon: '📊', text: 'NBOT Analysis', query: 'Show me NBOT breakdown by region' },
                { icon: '📅', text: 'Schedule Optimization', query: 'Analyze schedule optimization for next week' },
                { icon: '✅', text: 'Training Compliance', query: 'Check training compliance status' },
                { icon: '📋', text: 'Customer Report', query: 'Generate customer overview report' },
              ].map((chip, idx) => (
                <button
                  key={idx}
                  onClick={() => onSubmit(chip.query)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.5rem 1rem',
                    borderRadius: '4px',
                    background: THEME.bgCard,
                    border: `1px solid ${THEME.borderMedium}`,
                    color: THEME.textSecondary,
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = THEME.cyan;
                    e.currentTarget.style.color = THEME.cyan;
                    e.currentTarget.style.boxShadow = `0 0 15px ${THEME.cyanGlow}`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = THEME.borderMedium;
                    e.currentTarget.style.color = THEME.textSecondary;
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  <span>{chip.icon}</span>
                  <span>{chip.text}</span>
                </button>
              ))}
            </div>
          )}
          
          {/* File Upload Section */}
          {selectedFiles.length > 0 && (
            <div style={{ marginBottom: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {selectedFiles.map((file, index) => (
                <div 
                  key={index}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.5rem 0.75rem',
                    background: THEME.bgCard,
                    border: `1px solid ${THEME.borderMedium}`,
                    borderRadius: '4px'
                  }}
                >
                  <svg style={{ width: '14px', height: '14px', color: THEME.cyan }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <span style={{ fontSize: '0.85rem', color: THEME.textSecondary }}>{file.name}</span>
                  <span style={{ fontSize: '0.7rem', color: THEME.textMuted }}>({(file.size / 1024).toFixed(1)} KB)</span>
                  <button
                    onClick={() => handleRemoveFile(index)}
                    style={{ marginLeft: '0.25rem', padding: '0.25rem', background: 'transparent', border: 'none', cursor: 'pointer' }}
                  >
                    <svg style={{ width: '12px', height: '12px', color: THEME.red }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
              <button
                onClick={handleClearFiles}
                style={{
                  padding: '0.5rem 0.75rem',
                  background: 'rgba(255, 71, 87, 0.1)',
                  border: `1px solid rgba(255, 71, 87, 0.3)`,
                  borderRadius: '4px',
                  fontSize: '0.85rem',
                  color: THEME.red,
                  cursor: 'pointer'
                }}
              >
                Clear All
              </button>
            </div>
          )}

          {/* Input Row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            
            {/* Hidden File Input */}
            <input
              type="file"
              id="fileUpload"
              multiple
              accept=".pdf,.doc,.docx,.txt,.csv,.xlsx,.xls,.json,.md"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            
            {/* Upload Button */}
            <label
              htmlFor="fileUpload"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '48px',
                height: '48px',
                background: THEME.bgCard,
                border: `1px solid ${THEME.borderMedium}`,
                borderRadius: '4px',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                flexShrink: 0
              }}
            >
              <svg style={{ width: '20px', height: '20px', color: THEME.cyan }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            </label>
            
            {/* Input Form */}
            <div style={{ flex: 1 }}>
              <InputForm 
                onSubmit={(query) => {
                  onSubmit(query, selectedFiles.length > 0 ? selectedFiles : undefined);
                  setSelectedFiles([]);
                }} 
                isLoading={isLoading} 
                context="chat"
              />
            </div>
          </div>

          {/* File Count */}
          {selectedFiles.length > 0 && (
            <div style={{ marginTop: '0.5rem', textAlign: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: THEME.textMuted }}>
                {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
              </span>
            </div>
          )}
          
          {/* Cancel button */}
          {isLoading && (
            <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'center' }}>
              <button
                onClick={onCancel}
                style={{
                  padding: '0.5rem 1.5rem',
                  background: 'rgba(255, 71, 87, 0.1)',
                  border: `1px solid rgba(255, 71, 87, 0.5)`,
                  borderRadius: '4px',
                  fontSize: '0.85rem',
                  color: THEME.red,
                  cursor: 'pointer',
                  transition: 'all 0.3s ease'
                }}
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ===== CSS ANIMATIONS ===== */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Orbitron:wght@400;500;600;700;800;900&display=swap');
        
        @keyframes gridScroll {
          0% { transform: translate(0, 0); }
          100% { transform: translate(80px, 80px); }
        }

        @keyframes statusPulse {
          0%, 100% { 
            box-shadow: 0 0 8px currentColor;
          }
          50% { 
            box-shadow: 0 0 16px currentColor, 0 0 24px currentColor;
          }
        }

        @keyframes spinSlow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        @keyframes gradientShift {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }

        @keyframes scanHorizontal {
          0% { transform: translateX(-100%); opacity: 0; }
          50% { opacity: 1; }
          100% { transform: translateX(100%); opacity: 0; }
        }
        
        @keyframes highlight-flash {
          0%, 100% { background-color: transparent; }
          50% { background-color: rgba(0, 212, 255, 0.2); }
        }
        
        .highlight-flash {
          animation: highlight-flash 2s ease-in-out;
        }
      `}</style>
    </div>
  );
}
