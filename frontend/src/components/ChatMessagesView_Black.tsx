// ============================================================================
// IMPORTS SECTION
// ============================================================================
/**
 * React and Type Imports
 * - React type for TypeScript component definitions
 * - useState: Manages copy button state
 * - ReactNode: Type for any React element that can be rendered
 */
import type React from "react";
import { useState, ReactNode } from "react";

/**
 * UI Component Library Imports
 * - ScrollArea: Scrollable container for chat messages
 * - Button: Reusable button component
 * - Badge: Small label component for links/tags
 */
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";


/**
 * Icon Imports from Lucide React
 * - Loader2: Spinning loader for "Thinking..." state
 * - Copy: Copy icon for message copy button
 * - CopyCheck: Checkmark icon shown after copying
 */
import { Loader2, Copy, CopyCheck, Download, Pin } from "lucide-react";

/**
 * Internal Component Imports
 * - InputForm: Text input component for user messages
 * - ActivityTimeline: Visual timeline showing AI processing steps
 */
import { InputForm } from "@/components/InputForm";
import { ActivityTimeline } from "@/components/ActivityTimeline";

/**
 * Markdown Processing Imports
 * - ReactMarkdown: Renders markdown content as React components
 * - remarkGfm: Plugin for GitHub Flavored Markdown support (tables, strikethrough, etc.)
 */
import ReactMarkdown from "react-markdown";
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

// PDF generation library (frontend-only)
import { jsPDF } from "jspdf";

/**
 * Utility Import
 * - cn: Class name utility for conditional/merged class names
 */
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

/**
 * Markdown Component Props Type
 * Defines props for custom markdown rendering components
 * - className: Optional CSS classes
 * - children: Content to render
 * - [key: string]: Any additional props passed through
 */
type MdComponentProps = {
  className?: string;
  children?: ReactNode;
  [key: string]: any;
};

/**
 * ProcessedEvent Interface
 * Represents an event in the AI's processing timeline
 * - title: Display name of the processing step
 * - data: Associated data/metadata for the event
 */
interface ProcessedEvent {
  title: string;
  data: any;
}

// ============================================================================
// MARKDOWN COMPONENTS CONFIGURATION
// ============================================================================
/**
 * Custom Markdown Components
 * 
 * Overrides default ReactMarkdown rendering to match APEX design system.
 * Each component is styled with Tailwind classes for consistent appearance.
 * 
 * This configuration ensures all markdown content (AI responses, user messages)
 * maintains visual consistency with the rest of the application.
 */
const mdComponents = {
  /**
   * Heading Level 1
   * Largest heading with significant top margin and bold weight
   */
  h1: ({ className, children, ...props }: MdComponentProps) => (
    <h1 className={cn("text-2xl font-bold mt-4 mb-2", className)} {...props}>
      {children}
    </h1>
  ),
  
  /**
   * Heading Level 2
   * Secondary heading, slightly smaller than h1
   */
  h2: ({ className, children, ...props }: MdComponentProps) => (
    <h2 className={cn("text-xl font-bold mt-3 mb-2", className)} {...props}>
      {children}
    </h2>
  ),
  
  /**
   * Heading Level 3
   * Tertiary heading for subsections
   */
  h3: ({ className, children, ...props }: MdComponentProps) => (
    <h3 className={cn("text-lg font-bold mt-3 mb-1", className)} {...props}>
      {children}
    </h3>
  ),
  
  /**
   * Paragraph
   * Standard text block with proper line height for readability
   */
  p: ({ className, children, ...props }: MdComponentProps) => (
    <p className={cn("mb-3 leading-7", className)} {...props}>
      {children}
    </p>
  ),
  
  /**
   * Anchor/Link
   * Styled as badges with blue text, opens in new tab for security
   */
  a: ({ className, children, href, ...props }: MdComponentProps) => (
    <Badge className="text-xs mx-0.5">
      <a
        className={cn("text-blue-400 hover:text-blue-300 text-xs", className)}
        href={href}
        target="_blank"  // Opens in new tab
        rel="noopener noreferrer"  // Security: prevents window.opener access
        {...props}
      >
        {children}
      </a>
    </Badge>
  ),
  
  /**
   * Unordered List
   * Bullet points with proper indentation
   */
  ul: ({ className, children, ...props }: MdComponentProps) => (
    <ul className={cn("list-disc pl-6 mb-4 space-y-2", className)} {...props}>
      {children}
    </ul>
  ),
  
  /**
   * Ordered List
   * Numbered list with proper indentation
   */
  ol: ({ className, children, ...props }: MdComponentProps) => (
    <ol className={cn("list-decimal pl-6 mb-3", className)} {...props}>
      {children}
    </ol>
  ),
  
  /**
   * List Item
   * Individual item in ordered or unordered lists
   */
  li: ({ className, children, ...props }: MdComponentProps) => (
    <li className={cn("leading-relaxed", className)} // better line height
    {...props}>
      {children}
    </li>
  ),
  
  /**
   * Blockquote
   * Styled with left border and italic text for quotations
   */
  blockquote: ({ className, children, ...props }: MdComponentProps) => (
    <blockquote
      className={cn(
        "border-l-4 border-neutral-600 pl-4 italic my-3 text-sm",
        className
      )}
      {...props}
    >
      {children}
    </blockquote>
  ),
  
  /**
   * Inline Code
   * Small code snippets within text, styled with dark background
   */
  code: ({ className, children, ...props }: MdComponentProps) => (
    <code
      className={cn(
        "bg-neutral-900 rounded px-1 py-0.5 font-mono text-xs",
        className
      )}
      {...props}
    >
      {children}
    </code>
  ),
  
  /**
   * Code Block
   * Multi-line code with syntax highlighting support
   * Horizontal scroll for long lines
   */
  pre: ({ className, children, ...props }: MdComponentProps) => (
    <pre
      className={cn(
        "bg-neutral-900 p-3 rounded-lg overflow-x-auto font-mono text-xs my-3",
        className
      )}
      {...props}
    >
      {children}
    </pre>
  ),
  
  /**
   * Horizontal Rule
   * Divider line between sections
   */
  hr: ({ className, ...props }: MdComponentProps) => (
    <hr className={cn("border-neutral-600 my-4", className)} {...props} />
  ),
  
  /**
   * Table Container
   * Wrapper with horizontal scroll for responsive tables
   */
  table: ({ className, children, ...props }: MdComponentProps) => (
    <div className="my-3 overflow-x-auto">
      <table className={cn("border-collapse w-full", className)} {...props}>
        {children}
      </table>
    </div>
  ),
  
  /**
   * Table Header Cell
   * Bold text with borders for table headers
   */
  th: ({ className, children, ...props }: MdComponentProps) => (
    <th
      className={cn(
        "border border-neutral-600 px-3 py-2 text-left font-bold",
        className
      )}
      {...props}
    >
      {children}
    </th>
  ),
  
  /**
   * Table Data Cell
   * Standard table cell with borders
   */
  td: ({ className, children, ...props }: MdComponentProps) => (
    <td
      className={cn("border border-neutral-600 px-3 py-2", className)}
      {...props}
    >
      {children}
    </td>
  ),
};

// ============================================================================
// HUMAN MESSAGE BUBBLE COMPONENT
// ============================================================================

/**
 * HumanMessageBubbleProps Interface
 * Props for rendering user messages in the chat
 */
interface HumanMessageBubbleProps {
  message: { content: string; id: string };
  mdComponents: typeof mdComponents;
}

/**
 * HumanMessageBubble Component
 * 
 * Renders user messages in a styled bubble on the right side of the chat.
 * Features:
 * - Blue text color to distinguish from AI messages
 * - Rounded corners with special rounded bottom-right for speech bubble effect
 * - Dark background (neutral-700) for contrast
 * - Markdown support for formatted user input
 * - Responsive max-width (100% mobile, 90% desktop)
 */
const HumanMessageBubble: React.FC<HumanMessageBubbleProps> = ({
  message,
  mdComponents,
}) => {
  return (
    <div className="text-blue-500 text-sm bg-white rounded-4xl break-words min-h-5 bg-neutral-800 px-1 py-0 max-w-[100%] sm:max-w-[90%] px-4 pt-2 rounded-br-sm">
      <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm, remarkBreaks]}>
        {message.content}
      </ReactMarkdown>
    </div>
  );
};

// ============================================================================
// AI MESSAGE BUBBLE COMPONENT
// ============================================================================

/**
 * AiMessageBubbleProps Interface
 * Extended props for AI messages with additional features
 */
interface AiMessageBubbleProps {
  message: { content: string; id: string };
  mdComponents: typeof mdComponents;
  handleCopy: (text: string, messageId: string) => void;  // Copy to clipboard handler
  copiedMessageId: string | null;  // Track which message was copied
  agent?: string;  // Which AI agent sent this message
  finalReportWithCitations?: boolean;  // Is this the final report
  processedEvents: ProcessedEvent[];  // Timeline events to display
  websiteCount: number;  // Number of websites analyzed
  isLoading: boolean;  // Loading state for timeline
}

/**
 * AiMessageBubble Component
 * 
 * Complex component that renders AI responses with multiple display modes:
 * 
 * 1. Direct Display Mode: For interactive_planner_agent or final reports
 *    - Shows content immediately with full formatting
 *    - Includes copy button
 *    - May include timeline for planning agent
 * 
 * 2. Timeline-Only Mode: For first AI message with processing events
 *    - Shows ActivityTimeline component
 *    - Hides content from research agents
 *    - Shows accumulated content from other agents
 * 
 * 3. Fallback Mode: Standard message display
 *    - Shows content with copy button
 *    - No timeline
 * 
 * The component intelligently determines which mode to use based on:
 * - Agent type (interactive_planner_agent, report_composer_with_citations, etc.)
 * - Presence of processedEvents
 * - finalReportWithCitations flag
 */
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
  /**
   * Timeline Display Logic
   * Show timeline if we have events to display (typically first AI message)
   */
  const shouldShowTimeline = processedEvents.length > 0;
  
  /**
   * Direct Display Logic
   * Bypass timeline-only mode for specific agents or final report
   * These messages should always show their content directly
   */
  const shouldDisplayDirectly = 
    agent === "interactive_planner_agent" || 
    (agent === "report_composer_with_citations" && finalReportWithCitations);
  
  // ========================================================================
  // RENDER MODE 1: DIRECT DISPLAY
  // ========================================================================
  if (shouldDisplayDirectly) {
    return (
      <div className="relative break-words flex flex-col w-full">
        {/* Timeline for planning agent (shows processing steps) */}
        {shouldShowTimeline && agent === "interactive_planner_agent" && (
          <div className="w-full mb-2">
            <ActivityTimeline 
              processedEvents={processedEvents}
              isLoading={isLoading}
              websiteCount={websiteCount}
            />
          </div>
        )}
        
        {/* Main content with copy button */}
        <div className="flex items-start gap-3">



          {/* Message content with enhanced text size for readability */}
          <div className="flex-1 bg-neutral-800 text-neutral-100 rounded-2xl p-4 shadow max-w-[99%] text-base leading-relaxed">
          <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm, remarkBreaks]}>
           {message.content}
          </ReactMarkdown>
          </div>

          

          {/* Copy button with visual feedback */}
          <button
            onClick={() => handleCopy(message.content, message.id)}
            className="p-1 hover:bg-neutral-700 rounded"
          >
            {copiedMessageId === message.id ? (
              <CopyCheck className="h-4 w-4 text-green-500" />  // Success state
            ) : (
              <Copy className="h-4 w-4 text-neutral-400" />  // Default state
            )}
          </button>
        </div>
      </div>
    );
  } 
  
  // ========================================================================
  // RENDER MODE 2: TIMELINE-FOCUSED DISPLAY
  // ========================================================================
  else if (shouldShowTimeline) {
    return (
      <div className="relative break-words flex flex-col w-full">
        {/* Primary focus: Activity Timeline */}
        <div className="w-full">
          <ActivityTimeline 
            processedEvents={processedEvents}
            isLoading={isLoading}
            websiteCount={websiteCount}
          />
        </div>
        
        {/* Conditional content display */}
        {/* Only show if:
            1. Content exists and isn't empty
            2. NOT from interactive_planner_agent (avoid duplication)
        */}
        {message.content && message.content.trim() && agent !== "interactive_planner_agent" && (
          <div className="flex items-start gap-3 mt-2">
            <div className="flex-1 bg-neutral-800 text-neutral-100 rounded-2xl p-4 shadow max-w-[95%]">
              <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm, remarkBreaks]}>
                {message.content}
              </ReactMarkdown>
            </div>
            <button
              onClick={() => handleCopy(message.content, message.id)}
              className="p-1 hover:bg-neutral-700 rounded"
            >
              {copiedMessageId === message.id ? (
                <CopyCheck className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4 text-neutral-400" />
              )}
            </button>
          </div>
        )}
      </div>
    );
  } 
  
  // ========================================================================
  // RENDER MODE 3: STANDARD FALLBACK
  // ========================================================================
  else {
    return (
      <div className="relative break-words flex flex-col w-full">
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm, remarkBreaks]}>
              {message.content}
            </ReactMarkdown>
          </div>
          <button
            onClick={() => handleCopy(message.content, message.id)}
            className="p-1 hover:bg-neutral-700 rounded"
          >
            {copiedMessageId === message.id ? (
              <CopyCheck className="h-4 w-4 text-green-500" />
            ) : (
              <Copy className="h-4 w-4 text-neutral-400" />
            )}
          </button>
        </div>
      </div>
    );
  }
};

// ============================================================================
// MAIN CHAT MESSAGES VIEW COMPONENT
// ============================================================================

/**
 * ChatMessagesViewProps Interface
 * Props for the main chat interface component
 */
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
  onSubmit: (query: string, files?: File[]) => void;  // <-- ADDED files?: File[]
  onCancel: () => void;
  displayData: string | null;
  messageEvents: Map<string, ProcessedEvent[]>;
  websiteCount: number;
}

/**
 * ChatMessagesView Component
 * 
 * Main chat interface component that orchestrates the entire conversation UI.
 * 
 * Structure:
 * 1. Header - APEX branding and New Chat button
 * 2. Messages Area - Scrollable container with all messages
 * 3. Input Area - Text input and submit button at bottom
 * 
 * Features:
 * - Auto-scrolling to latest message
 * - Copy to clipboard for AI responses
 * - Loading indicators at multiple levels
 * - Timeline integration for AI processing visualization
 * - Responsive design with max-width containers
 * - Message alignment (human: right, AI: left)
 */
export function ChatMessagesView({
  messages,
  isLoading,
  scrollAreaRef,
  onSubmit,
  onCancel,
  messageEvents,
  websiteCount,
}: ChatMessagesViewProps) {
  /**
   * Local State: copiedMessageId
   * Tracks which message was recently copied for visual feedback
   * Auto-clears after 2 seconds
   */
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

  /**
   * Local State: selectedFiles
   * Tracks files selected for upload before sending message
   */
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  /**
   * Local State: insights and summaries per message
   * - highlightsByMessage: caches extracted key points
   * - summaryByMessage: caches short summaries
   * - expandedInsights / expandedSummary: control visibility toggles
   */
  const [highlightsByMessage, setHighlightsByMessage] = useState<Record<string, string[]>>({});
  const [summaryByMessage, setSummaryByMessage] = useState<Record<string, string>>({});
  const [expandedInsights, setExpandedInsights] = useState<Record<string, boolean>>({});
  const [expandedSummary, setExpandedSummary] = useState<Record<string, boolean>>({});

    /**
   * Local State: pinnedMessages
   * Stores message IDs that are pinned into the Session Summary bar.
   */
  const [pinnedMessages, setPinnedMessages] = useState<string[]>(() => {
    // Load from localStorage on mount
    try {
      const saved = localStorage.getItem('epc-pinned-messages');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  /**
   * Local State: messageTagsMap
   * Stores tags for each message: 'decision' | 'action' | 'idea'
   */
  const [messageTagsMap, setMessageTagsMap] = useState<Record<string, string>>(() => {
    try {
      const saved = localStorage.getItem('epc-message-tags');
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  /**
   * Local State: showSessionSummary
   * Controls visibility of the session summary sidebar
   */
  const [showSessionSummary, setShowSessionSummary] = useState(false);

  /**
   * Local State: cleanViewMessage
   * Stores message ID for clean view modal
   */
  const [cleanViewMessage, setCleanViewMessage] = useState<string | null>(null);

  // Tag dropdown state
  const [openTagDropdown, setOpenTagDropdown] = useState<string | null>(null);

  // 🎨 NEW: Settings State
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    colorScheme: 'blue',
    animationSpeed: 1,
    glowIntensity: 1,
    particleDensity: 4,
    spacing: 'normal',
    fontSize: 'normal',
    effectsEnabled: true,
    brightness: 1,
    focusMode: false, // NEW: Focus mode toggle
  });

  // 🌈 Color scheme configurations
  const colorSchemes = {
    blue: { from: 'indigo-400', via: 'blue-400', to: 'cyan-400', border: 'blue-500' },
    purple: { from: 'purple-400', via: 'violet-400', to: 'fuchsia-400', border: 'purple-500' },
    green: { from: 'emerald-400', via: 'green-400', to: 'teal-400', border: 'green-500' },
    red: { from: 'red-400', via: 'orange-400', to: 'yellow-400', border: 'red-500' },
    cyan: { from: 'cyan-400', via: 'sky-400', to: 'blue-400', border: 'cyan-500' },
  };

  const currentColors = colorSchemes[settings.colorScheme as keyof typeof colorSchemes];


  // 👤 Agent profiles with actual images
  const agentProfiles = {
    // Jordan - Root Orchestrator
    'root_orchestrator_agent': { name: 'Jordan', image: NexusImg, color: 'from-blue-500 to-cyan-500' },
    'jordan': { name: 'Jordan', image: NexusImg, color: 'from-blue-500 to-cyan-500' },
    'Jordan': { name: 'Jordan', image: NexusImg, color: 'from-blue-500 to-cyan-500' },
    
    // Atlas - NBOT Specialist
    'Atlas_agent': { name: 'Atlas', image: AtlasImg, color: 'from-purple-500 to-pink-500' },
    'Atlas': { name: 'Atlas', image: AtlasImg, color: 'from-purple-500 to-pink-500' },
    'Atlas': { name: 'Atlas', image: AtlasImg, color: 'from-purple-500 to-pink-500' },
    'nbot_agent': { name: 'Atlas', image: AtlasImg, color: 'from-purple-500 to-pink-500' },
    
    // Maestro - Scheduling Specialist
    'Maestro_agent': { name: 'Maestro', image: MaestroImg, color: 'from-green-500 to-teal-500' },
    'Maestro': { name: 'Maestro', image: MaestroImg, color: 'from-green-500 to-teal-500' },
    'Maestro': { name: 'Maestro', image: MaestroImg, color: 'from-green-500 to-teal-500' },
    'schedule_agent': { name: 'Maestro', image: MaestroImg, color: 'from-green-500 to-teal-500' },
    'scheduling_agent': { name: 'Maestro', image: MaestroImg, color: 'from-green-500 to-teal-500' },
    
    // Aegis - Training Compliance
    'Aegis_agent': { name: 'Aegis', image: AegisImg, color: 'from-yellow-500 to-orange-500' },
    'Aegis': { name: 'Aegis', image: AegisImg, color: 'from-yellow-500 to-orange-500' },
    'Aegis': { name: 'Aegis', image: AegisImg, color: 'from-yellow-500 to-orange-500' },
    'training_agent': { name: 'Aegis', image: AegisImg, color: 'from-yellow-500 to-orange-500' },
    'training_compliance_agent': { name: 'Aegis', image: AegisImg, color: 'from-yellow-500 to-orange-500' },
    
    // Sage - Research Specialistt
    'Sage_agent': { name: 'Sage', image: SageImg, color: 'from-cyan-500 to-blue-500' },
    'Sage': { name: 'Sage', image: SageImg, color: 'from-cyan-500 to-blue-500' },
    'Sage': { name: 'Sage', image: SageImg, color: 'from-cyan-500 to-blue-500' },
    'research_agent': { name: 'Sage', image: SageImg, color: 'from-cyan-500 to-blue-500' },
    
    // Generic fallback (shows for unmatched agents as "EPC Agent")
    'epc_agent': { name: 'EPC Agent', image: NexusImg, color: 'from-blue-500 to-cyan-500' },
    'EPC Agent': { name: 'EPC Agent', image: NexusImg, color: 'from-blue-500 to-cyan-500' },
  };

  /**
   * HTML Entity Decoder
   * Decodes HTML entities to prevent encoding corruption in exports
   * CRITICAL for PDF and HTML exports to work correctly
   */
  const decodeHtmlEntities = (text: string): string => {
    try {
      const textarea = document.createElement('textarea');
      textarea.innerHTML = text;
      const decoded = textarea.value;
      return decoded;
    } catch (err) {
      console.error('Failed to decode HTML entities:', err);
      return text; // Return original if decoding fails
    }
  };

  /**
   * File Upload Handlers
   * Manage file selection, removal, and clearing
   */
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

  /**
   * Copy to Clipboard Handler
   * Copies raw text and provides visual feedback
   */
  const handleCopy = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error("Failed to copy text:", err);
    }
  };

  /**
   * Copy as Markdown
   * Simply copies the original markdown content (same as raw message).
   */
  const handleCopyMarkdown = async (content: string, messageId: string) => {
    try {
      const markdown = content || "";
      await navigator.clipboard.writeText(markdown);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error("Failed to copy markdown:", err);
    }
  };

  /**
   * Copy as Plain Text
   * Strips basic markdown, bullets, and emojis to produce clean plain text.
   */
  const handleCopyPlainText = async (content: string, messageId: string) => {
    try {
      const text = (content || "")
        // Remove code fences
        .replace(/```[\s\S]*?```/g, "")
        // Remove inline code backticks
        .replace(/`([^`]+)`/g, "$1")
        // Remove markdown headings and list markers
        .replace(/^[#>\-\*\+]+\s+/gm, "")
        // Remove markdown links [text](url)
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1")
        // Remove images ![alt](url)
        .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, "$1")
        // Normalize multiple newlines
        .replace(/\n{3,}/g, "\n\n")
        // Remove most emojis (basic unicode ranges)
        .replace(
          /[\u{1F300}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu,
          ""
        )
        .trim();

      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error("Failed to copy plain text:", err);
    }
  };

  /**
   * Download HTML Handler (IMPROVED)
   * Creates a fully styled HTML file with proper markdown rendering.
   * Preserves all formatting including headers, lists, tables, code blocks, and links.
   */
  const handleDownloadHtml = (content: string, messageId: string) => {
    try {
      // CRITICAL: Decode HTML entities FIRST to prevent corruption
      const decodedContent = decodeHtmlEntities(content || "");
      
      // Convert markdown to HTML with basic rendering
      const markdownToHtml = (markdown: string): string => {
        let html = markdown;
        
        // Headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        
        // Bold
        html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
        html = html.replace(/__(.*?)__/gim, '<strong>$1</strong>');
        
        // Italic
        html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');
        html = html.replace(/_(.*?)_/gim, '<em>$1</em>');
        
        // Links
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        
        // Code blocks
        html = html.replace(/```([a-z]*)\n([\s\S]*?)```/gim, '<pre><code class="language-$1">$2</code></pre>');
        
        // Inline code
        html = html.replace(/`([^`]+)`/gim, '<code>$1</code>');
        
        // Lists
        html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
        html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        
        // Blockquotes
        html = html.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');
        
        // Horizontal rules
        html = html.replace(/^---$/gim, '<hr>');
        
        // Paragraphs
        html = html.replace(/\n\n/gim, '</p><p>');
        html = '<p>' + html + '</p>';
        
        // Clean up
        html = html.replace(/<p><\/p>/gim, '');
        html = html.replace(/<p>(<h[1-6]>)/gim, '$1');
        html = html.replace(/(<\/h[1-6]>)<\/p>/gim, '$1');
        html = html.replace(/<p>(<ul>)/gim, '$1');
        html = html.replace(/(<\/ul>)<\/p>/gim, '$1');
        html = html.replace(/<p>(<pre>)/gim, '$1');
        html = html.replace(/(<\/pre>)<\/p>/gim, '$1');
        
        return html;
      };

      const htmlContent = markdownToHtml(decodedContent);

      const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>EPC Intelligence Response</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: #e2e8f0;
      padding: 40px 20px;
      line-height: 1.7;
      min-height: 100vh;
    }
    .container {
      max-width: 900px;
      margin: 0 auto;
      background: #1e293b;
      border-radius: 16px;
      border: 1px solid rgba(148, 163, 184, 0.1);
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      overflow: hidden;
    }
    /* Animated Header */
    .header {
      position: relative;
      background: black;
      padding: 24px 32px;
      text-align: center;
      border-bottom: 1px solid rgba(148, 163, 184, 0.1);
      overflow: hidden;
    }
    
    /* Animated gradient background */
    .header-gradient {
      position: absolute;
      inset: 0;
      background: linear-gradient(135deg, 
        rgba(99, 102, 241, 0.05) 0%, 
        rgba(59, 130, 246, 0.05) 50%, 
        rgba(34, 211, 238, 0.05) 100%);
      background-size: 200% 200%;
      animation: gradient-shift 15s ease infinite;
    }
    
    /* Floating particles */
    .particles {
      position: absolute;
      inset: 0;
      overflow: hidden;
      pointer-events: none;
    }
    .particle {
      position: absolute;
      border-radius: 50%;
      background: rgba(99, 102, 241, 0.3);
    }
    .particle-1 {
      top: 25%;
      left: 10%;
      width: 8px;
      height: 8px;
      animation: float-slow 6s ease-in-out infinite;
    }
    .particle-2 {
      top: 50%;
      left: 30%;
      width: 4px;
      height: 4px;
      background: rgba(59, 130, 246, 0.4);
      animation: float-medium 4s ease-in-out infinite;
      animation-delay: 1s;
    }
    .particle-3 {
      top: 33%;
      right: 20%;
      width: 8px;
      height: 8px;
      background: rgba(34, 211, 238, 0.3);
      animation: float-slow 6s ease-in-out infinite;
      animation-delay: 2s;
    }
    .particle-4 {
      bottom: 25%;
      right: 40%;
      width: 4px;
      height: 4px;
      background: rgba(99, 102, 241, 0.4);
      animation: float-medium 4s ease-in-out infinite;
      animation-delay: 0.5s;
    }
    
    /* Header content */
    .header-content {
      position: relative;
      z-index: 10;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
    }
    
    /* Rotating ring logo */
    .logo-ring {
      position: relative;
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: linear-gradient(135deg, #6366f1, #3b82f6, #22d3ee);
      animation: spin-slow 8s linear infinite;
      box-shadow: 0 0 30px rgba(99, 102, 241, 0.5);
    }
    .logo-ring::before {
      content: '';
      position: absolute;
      inset: 0;
      border-radius: 50%;
      background: linear-gradient(135deg, #6366f1, #3b82f6, #22d3ee);
      opacity: 0.2;
      filter: blur(8px);
    }
    .logo-ring-inner {
      position: absolute;
      inset: 8px;
      border-radius: 50%;
      background: black;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .logo-icon {
      width: 20px;
      height: 20px;
      color: #818cf8;
    }
    
    /* Shimmer text */
    .shimmer-text {
      font-size: 36px;
      font-weight: 700;
      background: linear-gradient(
        to right,
        #818cf8 0%,
        #60a5fa 50%,
        #22d3ee 100%
      );
      background-size: 200% 100%;
      -webkit-background-clip: text;
      background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: shimmer 3s linear infinite;
      margin: 0;
    }
    
    .header p {
      font-size: 13px;
      color: #64748b;
      font-weight: 600;
      letter-spacing: 2px;
      margin: 0;
    }
    
    /* Scanning line */
    .scan-line {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 1px;
      background: linear-gradient(
        to right,
        transparent 0%,
        #3b82f6 50%,
        transparent 100%
      );
      opacity: 0.5;
      animation: scan-horizontal 4s linear infinite;
    }
    
    /* Animations */
    @keyframes gradient-shift {
      0%, 100% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
    }
    
    @keyframes shimmer {
      0% { background-position: -200% 0; }
      100% { background-position: 200% 0; }
    }
    
    @keyframes spin-slow {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    
    @keyframes float-slow {
      0%, 100% { transform: translateY(0px) translateX(0px); }
      50% { transform: translateY(-20px) translateX(10px); }
    }
    
    @keyframes float-medium {
      0%, 100% { transform: translateY(0px) translateX(0px); }
      50% { transform: translateY(-15px) translateX(-10px); }
    }
    
    @keyframes scan-horizontal {
      0% { transform: translateX(-100%); opacity: 0; }
      50% { opacity: 1; }
      100% { transform: translateX(100%); opacity: 0; }
    }
    .content {
      padding: 40px;
    }
    .content h1 {
      font-size: 32px;
      font-weight: 700;
      color: #f1f5f9;
      margin: 32px 0 16px 0;
      padding-bottom: 12px;
      border-bottom: 2px solid #3b82f6;
    }
    .content h2 {
      font-size: 26px;
      font-weight: 600;
      color: #cbd5e1;
      margin: 28px 0 14px 0;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(148, 163, 184, 0.2);
    }
    .content h3 {
      font-size: 22px;
      font-weight: 600;
      color: #94a3b8;
      margin: 24px 0 12px 0;
    }
    .content p {
      margin: 16px 0;
      color: #cbd5e1;
      font-size: 16px;
      line-height: 1.8;
    }
    .content ul, .content ol {
      margin: 16px 0;
      padding-left: 32px;
      color: #cbd5e1;
    }
    .content li {
      margin: 10px 0;
      line-height: 1.7;
      color: #cbd5e1;
    }
    .content li::marker {
      color: #3b82f6;
      font-weight: 600;
    }
    .content a {
      color: #60a5fa;
      text-decoration: none;
      border-bottom: 1px solid rgba(96, 165, 250, 0.3);
      transition: all 0.2s;
      padding: 2px 4px;
      border-radius: 3px;
    }
    .content a:hover {
      background: rgba(96, 165, 250, 0.1);
      border-bottom-color: #60a5fa;
    }
    .content blockquote {
      margin: 20px 0;
      padding: 16px 24px;
      background: rgba(59, 130, 246, 0.05);
      border-left: 4px solid #3b82f6;
      border-radius: 0 8px 8px 0;
      color: #cbd5e1;
      font-style: italic;
    }
    .content code {
      background: rgba(100, 116, 139, 0.2);
      padding: 3px 8px;
      border-radius: 4px;
      font-family: "Courier New", monospace;
      font-size: 14px;
      color: #fbbf24;
      border: 1px solid rgba(148, 163, 184, 0.1);
    }
    .content pre {
      background: #0f172a;
      padding: 20px;
      border-radius: 8px;
      overflow-x: auto;
      margin: 20px 0;
      border: 1px solid rgba(148, 163, 184, 0.1);
    }
    .content pre code {
      background: none;
      padding: 0;
      border: none;
      color: #94a3b8;
      font-size: 14px;
      line-height: 1.6;
    }
    .content table {
      width: 100%;
      border-collapse: collapse;
      margin: 24px 0;
      background: rgba(15, 23, 42, 0.5);
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid rgba(148, 163, 184, 0.1);
    }
    .content th {
      background: rgba(59, 130, 246, 0.15);
      color: #f1f5f9;
      font-weight: 600;
      padding: 14px 16px;
      text-align: left;
      border-bottom: 2px solid #3b82f6;
    }
    .content td {
      padding: 12px 16px;
      border-bottom: 1px solid rgba(148, 163, 184, 0.1);
      color: #cbd5e1;
    }
    .content tr:hover {
      background: rgba(59, 130, 246, 0.05);
    }
    .content hr {
      border: none;
      border-top: 1px solid rgba(148, 163, 184, 0.2);
      margin: 32px 0;
    }
    .content strong {
      color: #f1f5f9;
      font-weight: 600;
    }
    .footer {
      padding: 24px 40px;
      background: rgba(15, 23, 42, 0.5);
      border-top: 1px solid rgba(148, 163, 184, 0.1);
      text-align: center;
      color: #64748b;
      font-size: 14px;
    }
    @media print {
      body { background: white; color: black; }
      .container { border: none; box-shadow: none; }
      .header { background: #3b82f6; print-color-adjust: exact; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <!-- Animated gradient background -->
      <div class="header-gradient"></div>
      
      <!-- Floating particles -->
      <div class="particles">
        <div class="particle particle-1"></div>
        <div class="particle particle-2"></div>
        <div class="particle particle-3"></div>
        <div class="particle particle-4"></div>
      </div>
      
      <!-- Content -->
      <div class="header-content">
        <!-- Rotating ring logo -->
        <div class="logo-ring">
          <div class="logo-ring-inner">
            <svg class="logo-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        </div>
        
        <!-- Title with shimmer -->
        <div class="header-text">
          <h1 class="shimmer-text">EPC Intelligence</h1>
          <p>EXCELLENCE PERFORMANCE CENTER</p>
        </div>
      </div>
      
      <!-- Scanning line at bottom -->
      <div class="scan-line"></div>
    </div>
    <div class="content">
      ${htmlContent}
    </div>
    <div class="footer">
      Generated by EPC Intelligence on ${new Date().toLocaleDateString('en-US', { 
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

  /**
   * Download PDF Handler (IMPROVED)
   * Generates a well-formatted multi-page PDF with preserved structure.
   * Handles headers, lists, spacing, and maintains readability.
   */
  const handleDownloadPdf = (content: string, messageId: string) => {
    try {
      // Data arrives clean from backend - normalize for jsPDF compatibility
      const safeContent = (content || "")
        .normalize('NFC')  // Normalize Unicode to prevent jsPDF corruption
        .replace(/[\u{1F300}-\u{1FAFF}]/gu, '')  // Strip emojis that break jsPDF
        .trim();
      
      const doc = new jsPDF({
        unit: "pt",
        format: "a4",
        compress: true,
      });

      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      const margin = 50;
      const maxWidth = pageWidth - margin * 2;
      let cursorY = margin;
      const lineHeight = 16;
      const paragraphSpacing = 20;

      // ========================================================================
      // ADVANCED TEXT CLEANING - Removes citations and cleans markdown
      // ========================================================================
      const cleanText = (text: string): string => {
        let cleaned = text;
        
        // CRITICAL: Remove citation URLs like [source](https://vertexaisearch.cloud.google.com/...)
        // This regex finds [text](url) patterns and keeps only the text
        cleaned = cleaned.replace(/\[([^\]]+)\]\(https?:\/\/[^\)]+\)/g, '');
        
        // Remove standalone URLs that might remain
        cleaned = cleaned.replace(/https?:\/\/\S+/g, '');
        
        // Clean markdown formatting
        cleaned = cleaned.replace(/\*\*(.*?)\*\*/g, '$1');  // Bold
        cleaned = cleaned.replace(/__(.*?)__/g, '$1');      // Bold alt
        cleaned = cleaned.replace(/\*(.*?)\*/g, '$1');      // Italic
        cleaned = cleaned.replace(/_(.*?)_/g, '$1');        // Italic alt
        cleaned = cleaned.replace(/`([^`]+)`/g, '$1');      // Inline code
        
        // Remove any remaining bracket artifacts
        cleaned = cleaned.replace(/\[\]/g, '');
        cleaned = cleaned.replace(/\(\)/g, '');
        
        // Clean up excessive whitespace
        cleaned = cleaned.replace(/\s+/g, ' ');
        cleaned = cleaned.trim();
        
        return cleaned;
      };

      // Header with EPC branding
      doc.setFillColor(59, 130, 246);
      doc.rect(0, 0, pageWidth, 80, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(24);
      doc.text("EPC Intelligence", pageWidth / 2, 35, { align: 'center' });
      doc.setFontSize(12);
      doc.setFont("helvetica", "normal");
      doc.text("Excellence Performance Center - AI Agent Response", pageWidth / 2, 55, { align: 'center' });
      
      cursorY = 110;

      // Process normalized content
      const lines = safeContent.split('\n');
      
      for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        if (!line) {
          cursorY += 12;
          continue;
        }

        // Headers H1
        if (line.startsWith('# ')) {
          if (cursorY > 130) cursorY += 30;
          doc.setFont("helvetica", "bold");
          doc.setFontSize(18);
          doc.setTextColor(30, 41, 59);
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
          doc.setDrawColor(59, 130, 246);
          doc.line(margin, cursorY + 2, pageWidth - margin, cursorY + 2);
          cursorY += 25;
          continue;
        }

        // Headers H2
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

        // Headers H3
        if (line.startsWith('### ')) {
          if (cursorY > 130) cursorY += 18;
          doc.setFont("helvetica", "bold");
          doc.setFontSize(12);
          doc.setTextColor(71, 85, 105);
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
          
          // Blue bullet point
          doc.setFillColor(59, 130, 246);
          doc.circle(margin + 5, cursorY - 3, 2.5, 'F');
          
          const listLines = doc.splitTextToSize(line, maxWidth - 25);
          listLines.forEach((listLine: string, index: number) => {
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
            
            // Blue number
            doc.setTextColor(59, 130, 246);
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

        // Code blocks
        if (line.startsWith('```')) {
          cursorY += 10;
          const codeBlockStartY = cursorY - 8;
          let codeBlockHeight = 16;
          
          i++;
          const codeLines = [];
          while (i < lines.length && !lines[i].trim().startsWith('```')) {
            codeLines.push(lines[i]);
            i++;
          }
          
          doc.setFont("courier", "normal");
          doc.setFontSize(9);
          doc.setTextColor(51, 65, 85);
          
          codeLines.forEach((codeLine: string) => {
            if (cursorY > pageHeight - margin - 30) {
              doc.addPage();
              cursorY = margin;
            }
            doc.text(codeLine.substring(0, 90), margin + 10, cursorY); // Truncate long lines
            cursorY += 13;
            codeBlockHeight += 13;
          });
          
          doc.setFillColor(241, 245, 249);
          doc.rect(margin, codeBlockStartY, maxWidth, codeBlockHeight, 'F');
          
          cursorY += 18;
          continue;
        }

        // Regular paragraphs - CLEAN TEXT HERE
        doc.setFont("helvetica", "normal");
        doc.setFontSize(10);
        doc.setTextColor(55, 65, 81);
        
        line = cleanText(line);
        
        // Skip empty lines after cleaning
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
        
        const footerText = `Generated by EPC Intelligence on ${new Date().toLocaleDateString('en-US', { 
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

  /**
   * Download TXT Handler
   * Saves the AI response as a .txt file to the user's default Downloads folder.
   */
  const handleDownloadTxt = (content: string, messageId: string) => {
    try {
      const text = content || "";
      const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
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

  /**
   * Generate Highlight Key Points
   * Lightweight, client-side extraction of 3–5 sentences as key bullets.
   */
  const handleGenerateHighlights = (content: string, messageId: string) => {
    const raw = content || "";

    // Very simple markdown cleanup
    const cleaned = raw
      .replace(/```[\s\S]*?```/g, " ")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/^[#>\-\*\+]+\s+/gm, "")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1")
      .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, "$1")
      .replace(/\s+/g, " ")
      .trim();

    if (!cleaned) {
      return;
    }

    // Split into sentences (very simple heuristic)
    const sentences = cleaned
      .split(/(?<=[\.!\?])\s+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    // Score sentences by length (proxy for information density)
    const scored = sentences
      .map((s) => ({ text: s, score: Math.min(s.length, 300) }))
      .sort((a, b) => b.score - a.score);

    const top = scored.slice(0, 5).map((s) => s.text);

    setHighlightsByMessage((prev) => ({
      ...prev,
      [messageId]: top,
    }));
    setExpandedInsights((prev) => ({
      ...prev,
      [messageId]: true,
    }));
  };

  /**
   * Generate Short Summary
   * Produces a 2–3 sentence summary using simple heuristics (no LLM).
   */
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

    if (!cleaned) {
      return;
    }

    const sentences = cleaned
      .split(/(?<=[\.!\?])\s+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    const maxSentences = 3;
    const summarySentences = sentences.slice(0, maxSentences);
    const summary = summarySentences.join(" ");

    setSummaryByMessage((prev) => ({
      ...prev,
      [messageId]: summary,
    }));
    setExpandedSummary((prev) => ({
      ...prev,
      [messageId]: true,
    }));
  };



  /**
   * Toggle Pin Message
   * Adds or removes message from pinned list
   */
  const handleTogglePin = (messageId: string) => {
    setPinnedMessages((prev) => {
      const updated = prev.includes(messageId)
        ? prev.filter((id) => id !== messageId)
        : [...prev, messageId];
      
      // Persist to localStorage
      try {
        localStorage.setItem('epc-pinned-messages', JSON.stringify(updated));
      } catch (err) {
        console.error('Failed to save pinned messages:', err);
      }
      
      return updated;
    });
  };

  /**
   * Set Message Tag
   * Assigns a tag (decision/action/idea) to a message
   */
  const handleSetTag = (messageId: string, tag: 'decision' | 'action' | 'idea') => {
    setMessageTagsMap((prev) => {
      const updated = { ...prev, [messageId]: tag };
      
      // Persist to localStorage
      try {
        localStorage.setItem('epc-message-tags', JSON.stringify(updated));
      } catch (err) {
        console.error('Failed to save message tags:', err);
      }
      
      return updated;
    });
  };

  /**
   * Remove Message Tag
   * Clears the tag from a message
   */
  const handleRemoveTag = (messageId: string) => {
    setMessageTagsMap((prev) => {
      const updated = { ...prev };
      delete updated[messageId];
      
      // Persist to localStorage
      try {
        localStorage.setItem('epc-message-tags', JSON.stringify(updated));
      } catch (err) {
        console.error('Failed to remove message tag:', err);
      }
      
      return updated;
    });
  };

  /**
   * Scroll to Message
   * Smoothly scrolls to a specific message in the chat
   */
  const handleScrollToMessage = (messageId: string) => {
    const element = document.getElementById(`message-${messageId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Flash highlight effect
      element.classList.add('highlight-flash');
      setTimeout(() => element.classList.remove('highlight-flash'), 2000);
    }
  };

  /**
   * New Chat Handler
   * Refreshes the page to start a new conversation
   */
  const handleNewChat = () => {
    window.location.reload();
  };

  /**
   * Find Last AI Message
   * Used to determine where to show loading indicators
   * Timeline only shows on the most recent AI message
   */
  const lastAiMessage = messages.slice().reverse().find(m => m.type === "ai");
  const lastAiMessageId = lastAiMessage?.id;

  return (
    <div 
      className={`flex flex-col h-full w-full transition-all duration-500 ${
        settings.focusMode 
          ? 'bg-zinc-950' // Darker in focus mode
          : 'bg-zinc-900'
      }`}
      style={{ filter: `brightness(${settings.brightness})` }}
    >
      
      {/* EPIC ANIMATED HEADER */}
      <div className={`relative border-b border-white/10 overflow-hidden transition-all duration-500 ${
        settings.focusMode ? 'bg-zinc-950' : 'bg-black'
      }`}>
        {/* Animated gradient background - Hide in Focus Mode */}
        {!settings.focusMode && settings.effectsEnabled && (
          <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/5 via-blue-500/5 to-cyan-500/5 animate-gradient-x" />
        )}
        
        {/* Floating particles - Hide in Focus Mode */}
        {!settings.focusMode && settings.effectsEnabled && settings.particleDensity > 0 && (
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {settings.particleDensity >= 2 && <div className="absolute top-1/4 left-[10%] w-2 h-2 bg-indigo-400/30 rounded-full animate-float-slow" />}
            {settings.particleDensity >= 4 && <div className="absolute top-1/2 left-[30%] w-1 h-1 bg-blue-400/40 rounded-full animate-float-medium" style={{ animationDelay: '1s' }} />}
            {settings.particleDensity >= 6 && <div className="absolute top-1/3 right-[20%] w-2 h-2 bg-cyan-400/30 rounded-full animate-float-slow" style={{ animationDelay: '2s' }} />}
            {settings.particleDensity >= 8 && <div className="absolute bottom-1/4 right-[40%] w-1 h-1 bg-indigo-400/40 rounded-full animate-float-medium" style={{ animationDelay: '0.5s' }} />}
          </div>
        )}

        <div className="max-w-[95%] xl:max-w-[1300px] 2xl:max-w-[1400px] mx-auto px-6 py-6 relative">
          <div className="flex items-center justify-between gap-8">
            
            {/* Left: Animated Logo & Title */}
            <div className="flex items-center gap-4">
              {/* Rotating ring logo */}
              <div className="relative w-16 h-16 rounded-full border-2 border-transparent bg-gradient-to-br from-indigo-500 via-blue-500 to-cyan-500 animate-spin-slow">
                <div className="absolute inset-0 rounded-full bg-gradient-to-br from-indigo-500 via-blue-500 to-cyan-500 animate-spin-slow opacity-20 blur-sm" />
                <div className="absolute inset-0 rounded-full border-2 border-transparent bg-gradient-to-br from-indigo-500 via-blue-500 to-cyan-500 bg-clip-border animate-pulse" 
                     style={{ 
                       WebkitMask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)',
                       WebkitMaskComposite: 'xor',
                       maskComposite: 'exclude',
                       padding: '2px'
                     }} />
                <div className="absolute inset-2 rounded-full bg-black flex items-center justify-center">
                  <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
              </div>

              {/* Title with shimmer effect */}
              <div className="relative">
                <h1 
                  className="text-3xl font-bold bg-clip-text text-transparent animate-shimmer"
                  style={{
                    backgroundImage: settings.colorScheme === 'blue' ? 'linear-gradient(to right, #818cf8, #60a5fa, #22d3ee)' :
                                     settings.colorScheme === 'purple' ? 'linear-gradient(to right, #c084fc, #a78bfa, #e879f9)' :
                                     settings.colorScheme === 'green' ? 'linear-gradient(to right, #34d399, #10b981, #14b8a6)' :
                                     settings.colorScheme === 'red' ? 'linear-gradient(to right, #f87171, #fb923c, #fbbf24)' :
                                     'linear-gradient(to right, #22d3ee, #0ea5e9, #3b82f6)',
                    backgroundSize: '200% 100%'
                  }}
                >
                  EPC Intelligence
                </h1>
                <p className="text-md text-slate-500 tracking-wider">EXCELLENCE PERFORMANCE CENTER</p>
                
                {/* Animated underline */}
                <div className="absolute -bottom-1 left-0 h-[2px] w-full overflow-hidden">
                  <div className="h-full w-1/3 bg-gradient-to-r from-transparent via-cyan-500 to-transparent animate-scan" />
                </div>
              </div>
            </div>

            {/* Center: Status Indicators */}
            <div className="hidden md:flex items-center gap-8">
              {/* Online status */}
              <div className="flex items-center gap-3 px-3 py-2.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                <div className="w-4 h-4 bg-gradient-to-br from-indigo-500 via-blue-500 to-cyan-500emerald-400 rounded-full animate-pulse-slow" />
                <span className="text-md text-emerald-400 font-medium">AGENTS ONLINE</span>
              </div>
              
              {/* Processing indicator */}
              {isLoading && (
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-full bg-blue-500/10 border border-blue-500/20">
                  <div className="flex gap-1">
                    <div className="w-2 h-6 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-6 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-6 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                  <span className="text-md text-blue-400 font-medium">PROCESSING</span>
                </div>
              )}
            </div>

            {/* Right: Session Summary + Focus Mode + Settings + New Chat */}
            <div className="flex items-center gap-3 ml-auto">
              {/* Session Summary Toggle */}
              <button 
                onClick={() => setShowSessionSummary(!showSessionSummary)} 
                className="relative group"
              >
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 via-blue-500 to-cyan-500 rounded-xl blur-md opacity-0 group-hover:opacity-40 transition-all duration-500" />
                <div className="relative flex items-center gap-2 px-4 py-2.5 bg-gradient-to-br from-zinc-900 to-zinc-800 border border-white/10 rounded-xl text-sm text-white hover:border-blue-500/50 transition-all duration-300 group-hover:scale-105">
                  <Pin className="w-4 h-4 text-amber-400" />
                  <span className="font-medium">Summary</span>
                  {pinnedMessages.length > 0 && (
                    <span className="ml-1 px-2 py-0.5 bg-amber-500/20 border border-amber-500/40 rounded-full text-xs text-amber-400">
                      {pinnedMessages.length}
                    </span>
                  )}
                </div>
              </button>

              {/* Focus Mode Quick Toggle */}
              <button 
                onClick={() => setSettings({ ...settings, focusMode: !settings.focusMode })} 
                className="relative group"
              >
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 via-blue-500 to-cyan-500 rounded-xl blur-md opacity-0 group-hover:opacity-40 transition-all duration-500" />
                <div className={`relative flex items-center gap-2 px-4 py-2.5 bg-gradient-to-br from-zinc-900 to-zinc-800 border rounded-xl text-sm transition-all duration-300 group-hover:scale-105 ${
                  settings.focusMode 
                    ? 'border-purple-500/50 text-purple-400' 
                    : 'border-white/10 text-white hover:border-blue-500/50'
                }`}>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  <span className="font-medium">{settings.focusMode ? 'Focus ON' : 'Focus'}</span>
                </div>
              </button>

              <button onClick={() => setShowSettings(!showSettings)} className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 via-blue-500 to-cyan-500 rounded-xl blur-md opacity-0 group-hover:opacity-40 transition-all duration-500" />
                <div className="relative flex items-center gap-2 px-4 py-2.5 bg-gradient-to-br from-zinc-900 to-zinc-800 border border-white/10 rounded-xl text-sm text-white hover:border-blue-500/50 transition-all duration-300 group-hover:scale-105">
                  <svg className="w-4 h-4 text-blue-400 group-hover:rotate-180 transition-transform duration-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span className="font-medium">Settings</span>
                </div>
              </button>
              <button onClick={handleNewChat} className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 via-blue-500 to-cyan-500 rounded-xl blur-md opacity-0 group-hover:opacity-60 transition-all duration-500 animate-pulse-glow" />
                <div className="relative flex items-center gap-2 px-5 py-2.5 bg-gradient-to-br from-zinc-900 to-zinc-800 border border-white/10 rounded-xl text-sm text-white hover:border-blue-500/50 transition-all duration-300 group-hover:scale-105">
                  <svg className="w-5 h-4 text-blue-400 group-hover:rotate-90 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <span className="font-medium">New Chat</span>
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Scanning line effect */}
        <div className="absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50 animate-scan-horizontal" />
      </div>

      {/* ⚙️ SETTINGS PANEL - ADD THIS ENTIRE BLOCK HERE */}
      <div className={`fixed top-0 right-0 h-full w-96 bg-zinc-950 border-l border-white/10 shadow-2xl transform transition-transform duration-300 z-50 ${showSettings ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="h-full flex flex-col">
          
          {/* Panel Header */}
          <div className="p-6 border-b border-white/10 bg-gradient-to-r from-indigo-500/10 via-blue-500/10 to-cyan-500/10">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">⚙️ Settings</h2>
              <button
                onClick={() => setShowSettings(false)}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Settings Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            
            {/* 🌈 Color Scheme */}
            <div>
              <label className="text-sm font-bold text-white mb-3 block">🌈 Color Scheme</label>
              <div className="grid grid-cols-5 gap-2">
                {Object.keys(colorSchemes).map((scheme) => (
                  <button
                    key={scheme}
                    onClick={() => setSettings({ ...settings, colorScheme: scheme })}
                    className={`h-10 rounded-lg border-2 transition-all ${
                      settings.colorScheme === scheme 
                        ? 'border-white scale-110' 
                        : 'border-white/20 hover:border-white/50'
                    }`}
                    style={{
                      background: scheme === 'blue' ? 'linear-gradient(to right, #818cf8, #60a5fa, #22d3ee)' :
                                  scheme === 'purple' ? 'linear-gradient(to right, #c084fc, #a78bfa, #e879f9)' :
                                  scheme === 'green' ? 'linear-gradient(to right, #34d399, #10b981, #14b8a6)' :
                                  scheme === 'red' ? 'linear-gradient(to right, #f87171, #fb923c, #fbbf24)' :
                                  'linear-gradient(to right, #22d3ee, #0ea5e9, #3b82f6)'
                    }}
                  />
                ))}
              </div>
            </div>

            {/* ⚡ Animation Speed */}
            <div>
              <label className="text-sm font-bold text-white mb-2 block">⚡ Animation Speed: {settings.animationSpeed}x</label>
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.1"
                value={settings.animationSpeed}
                onChange={(e) => setSettings({ ...settings, animationSpeed: parseFloat(e.target.value) })}
                className="w-full accent-blue-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>Slow</span>
                <span>Normal</span>
                <span>Fast</span>
              </div>
            </div>

            {/* 💡 Brightness */}
            <div>
              <label className="text-sm font-bold text-white mb-2 block">💡 Brightness: {Math.round(settings.brightness * 100)}%</label>
              <input
                type="range"
                min="0.5"
                max="1.5"
                step="0.1"
                value={settings.brightness}
                onChange={(e) => setSettings({ ...settings, brightness: parseFloat(e.target.value) })}
                className="w-full accent-blue-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>Dim</span>
                <span>Normal</span>
                <span>Bright</span>
              </div>
            </div>

            {/* 💫 Particle Density */}
            <div>
              <label className="text-sm font-bold text-white mb-2 block">💫 Particles: {settings.particleDensity}</label>
              <input
                type="range"
                min="0"
                max="12"
                step="1"
                value={settings.particleDensity}
                onChange={(e) => setSettings({ ...settings, particleDensity: parseInt(e.target.value) })}
                className="w-full accent-blue-500"
              />
              <div className="flex justify-between text-xs text-slate-500 mt-1">
                <span>None</span>
                <span>Some</span>
                <span>Many</span>
              </div>
            </div>

            {/* 📏 Spacing Mode */}
            <div>
              <label className="text-sm font-bold text-white mb-3 block">📏 Spacing Mode</label>
              <div className="grid grid-cols-3 gap-2">
                {['compact', 'normal', 'spacious'].map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setSettings({ ...settings, spacing: mode })}
                    className={`py-2 px-3 rounded-lg border-2 text-sm font-medium transition-all ${
                      settings.spacing === mode
                        ? 'border-blue-500 bg-blue-500/20 text-white'
                        : 'border-white/20 text-slate-400 hover:border-white/50'
                    }`}
                  >
                    {mode.charAt(0).toUpperCase() + mode.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* 🔤 Font Size */}
            <div>
              <label className="text-sm font-bold text-white mb-3 block">🔤 Font Size</label>
              <div className="grid grid-cols-3 gap-2">
                {['small', 'normal', 'large'].map((size) => (
                  <button
                    key={size}
                    onClick={() => setSettings({ ...settings, fontSize: size })}
                    className={`py-2 px-3 rounded-lg border-2 text-sm font-medium transition-all ${
                      settings.fontSize === size
                        ? 'border-blue-500 bg-blue-500/20 text-white'
                        : 'border-white/20 text-slate-400 hover:border-white/50'
                    }`}
                  >
                    {size.charAt(0).toUpperCase() + size.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {/* 🎭 Effects Toggle */}
            <div>
              <label className="flex items-center justify-between p-4 bg-white/5 rounded-lg border border-white/10 cursor-pointer hover:bg-white/10 transition-colors">
                <span className="text-sm font-bold text-white">🎭 Enable Animations</span>
                <input
                  type="checkbox"
                  checked={settings.effectsEnabled}
                  onChange={(e) => setSettings({ ...settings, effectsEnabled: e.target.checked })}
                  className="w-5 h-5 accent-blue-500"
                />
              </label>
            </div>

            {/* 🎯 Focus Mode Toggle */}
            <div>
              <label className="flex items-center justify-between p-4 bg-purple-500/10 rounded-lg border border-purple-500/30 cursor-pointer hover:bg-purple-500/20 transition-colors">
                <div className="flex flex-col gap-1">
                  <span className="text-sm font-bold text-white">🎯 Focus Mode</span>
                  <span className="text-xs text-slate-400">Minimal UI for deep work</span>
                </div>
                <input
                  type="checkbox"
                  checked={settings.focusMode}
                  onChange={(e) => setSettings({ ...settings, focusMode: e.target.checked })}
                  className="w-5 h-5 accent-purple-500"
                />
              </label>
            </div>

            {/* Reset Button */}
            <button
              onClick={() => setSettings({
                colorScheme: 'blue',
                animationSpeed: 1,
                glowIntensity: 1,
                particleDensity: 4,
                spacing: 'normal',
                fontSize: 'normal',
                effectsEnabled: true,
                brightness: 1,
              })}
              className="w-full py-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 font-bold hover:bg-red-500/30 transition-colors"
            >
              🔄 Reset to Defaults
            </button>
          </div>
        </div>
      </div>

      {/* Overlay when settings open */}
      {showSettings && (
        <div 
          className="fixed inset-0 bg-black/30 z-40"
          onClick={() => setShowSettings(false)}
        />
      )}

      {/* 📌 SESSION SUMMARY SIDEBAR */}
      <div className={`fixed top-0 left-0 h-full w-96 bg-zinc-950 border-r border-white/10 shadow-2xl transform transition-transform duration-300 z-50 ${showSessionSummary ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="h-full flex flex-col">
          
          {/* Sidebar Header */}
          <div className="p-6 border-b border-white/10 bg-gradient-to-r from-amber-500/10 via-yellow-500/10 to-amber-500/10">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Pin className="w-5 h-5 text-amber-400" />
                <h2 className="text-xl font-bold text-white">Session Summary</h2>
              </div>
              <button
                onClick={() => setShowSessionSummary(false)}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-xs text-slate-400 mt-1">Pinned insights from this conversation</p>
          </div>

          {/* Pinned Messages List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {pinnedMessages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-6">
                <Pin className="w-12 h-12 text-slate-600 mb-3" />
                <p className="text-sm text-slate-400 mb-2">No pinned messages yet</p>
                <p className="text-xs text-slate-500">Click the ⭐ button on AI responses to pin important insights here</p>
              </div>
            ) : (
              pinnedMessages.map((msgId) => {
                const msg = messages.find(m => m.id === msgId);
                if (!msg || msg.type !== 'ai') return null;
                
                const tag = messageTagsMap[msgId];
                const snippet = msg.content.substring(0, 150) + (msg.content.length > 150 ? '...' : '');
                
                return (
                  <div 
                    key={msgId}
                    className="bg-zinc-900/50 border border-white/10 rounded-lg p-4 hover:border-amber-500/30 transition-all cursor-pointer group"
                    onClick={() => {
                      handleScrollToMessage(msgId);
                      setShowSessionSummary(false);
                    }}
                  >
                    {/* Tag Badge */}
                    {tag && (
                      <div className="mb-2">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                          tag === 'decision' ? 'bg-green-500/20 text-green-400 border border-green-500/40' :
                          tag === 'action' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' :
                          'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                        }`}>
                          {tag === 'decision' ? '✅ Decision' : tag === 'action' ? '📝 Action Item' : '💡 Idea'}
                        </span>
                      </div>
                    )}
                    
                    {/* Agent Info */}
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 via-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs">
                        {msg.agent && agentProfiles[msg.agent as keyof typeof agentProfiles] ? (
                          <img 
                            src={agentProfiles[msg.agent as keyof typeof agentProfiles].image}
                            alt={agentProfiles[msg.agent as keyof typeof agentProfiles].name}
                            className="w-full h-full rounded-full object-cover"
                          />
                        ) : '⚡'}
                      </div>
                      <span className="text-xs font-medium text-slate-400">
                        {msg.agent && agentProfiles[msg.agent as keyof typeof agentProfiles] 
                          ? agentProfiles[msg.agent as keyof typeof agentProfiles].name 
                          : 'EPC Agent'}
                      </span>
                    </div>
                    
                    {/* Message Snippet */}
                    <p className="text-xs text-slate-300 line-clamp-3 mb-3">{snippet}</p>
                    
                    {/* Action Buttons */}
                    <div className="flex items-center justify-between pt-2 border-t border-white/5">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleScrollToMessage(msgId);
                          setShowSessionSummary(false);
                        }}
                        className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                        Jump to message
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTogglePin(msgId);
                        }}
                        className="text-xs text-red-400 hover:text-red-300"
                      >
                        Unpin
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Clear All Button */}
          {pinnedMessages.length > 0 && (
            <div className="p-4 border-t border-white/10">
              <button
                onClick={() => {
                  setPinnedMessages([]);
                  localStorage.removeItem('epc-pinned-messages');
                }}
                className="w-full py-2 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm font-medium hover:bg-red-500/30 transition-colors"
              >
                Clear All Pins
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Overlay when session summary open */}
      {showSessionSummary && (
        <div 
          className="fixed inset-0 bg-black/30 z-40"
          onClick={() => setShowSessionSummary(false)}
        />
      )}

      {/* 🔍 CLEAN VIEW MODAL */}
      {cleanViewMessage && (() => {
        const msg = messages.find(m => m.id === cleanViewMessage);
        if (!msg) return null;
        
        return (
          <>
            <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50" onClick={() => setCleanViewMessage(null)} />
            <div className="fixed inset-4 md:inset-10 z-50 flex items-center justify-center">
              <div className="bg-white w-full h-full rounded-2xl shadow-2xl flex flex-col max-w-5xl">
                
                {/* Modal Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-200">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 via-blue-500 to-cyan-500 flex items-center justify-center text-white">
                      {msg.agent && agentProfiles[msg.agent as keyof typeof agentProfiles] ? (
                        <img 
                          src={agentProfiles[msg.agent as keyof typeof agentProfiles].image}
                          alt={agentProfiles[msg.agent as keyof typeof agentProfiles].name}
                          className="w-full h-full rounded-full object-cover"
                        />
                      ) : '⚡'}
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-slate-900">Clean View</h3>
                      <p className="text-xs text-slate-500">
                        {msg.agent && agentProfiles[msg.agent as keyof typeof agentProfiles] 
                          ? agentProfiles[msg.agent as keyof typeof agentProfiles].name 
                          : 'EPC Agent'} Response
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setCleanViewMessage(null)}
                    className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Modal Content - Scrollable */}
                <div className="flex-1 overflow-y-auto p-8 bg-slate-50">
                  <div className="prose prose-slate max-w-none">
                    {/* Highlights Section */}
                    {highlightsByMessage[cleanViewMessage] && highlightsByMessage[cleanViewMessage].length > 0 && (
                      <div className="mb-6 p-4 bg-blue-50 border-l-4 border-blue-500 rounded-r">
                        <h4 className="text-sm font-bold text-blue-900 mb-3 flex items-center gap-2">
                          <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                          KEY INSIGHTS
                        </h4>
                        <ul className="space-y-2 text-sm text-slate-700">
                          {highlightsByMessage[cleanViewMessage].map((item, idx) => (
                            <li key={idx}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Summary Section */}
                    {summaryByMessage[cleanViewMessage] && (
                      <div className="mb-6 p-4 bg-emerald-50 border-l-4 border-emerald-500 rounded-r">
                        <h4 className="text-sm font-bold text-emerald-900 mb-2 flex items-center gap-2">
                          <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                          EXECUTIVE SUMMARY
                        </h4>
                        <p className="text-sm text-slate-700">{summaryByMessage[cleanViewMessage]}</p>
                      </div>
                    )}

                    {/* Main Content */}
                    <div className="text-slate-800 text-base leading-relaxed">
                      <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm, remarkBreaks]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>

                {/* Modal Footer - Actions */}
                <div className="p-6 border-t border-slate-200 bg-white flex justify-between items-center">
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleCopy(msg.content, msg.id)}
                      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm text-slate-700 flex items-center gap-2 transition-colors"
                    >
                      <Copy className="w-4 h-4" />
                      Copy
                    </button>
                    <button
                      onClick={() => handleDownloadPdf(msg.content, msg.id)}
                      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm text-slate-700 flex items-center gap-2 transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      PDF
                    </button>
                  </div>
                  <button
                    onClick={() => setCleanViewMessage(null)}
                    className="px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-lg text-sm text-white font-medium transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </>
        );
      })()}

      {/* 📌 SESSION SUMMARY SIDEBAR */}
      <div className={`fixed top-0 left-0 h-full w-96 bg-zinc-950 border-r border-white/10 shadow-2xl transform transition-transform duration-300 z-50 ${showSessionSummary ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="h-full flex flex-col">
          
          {/* Sidebar Header */}
          <div className="p-6 border-b border-white/10 bg-gradient-to-r from-amber-500/10 via-yellow-500/10 to-amber-500/10">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Pin className="w-5 h-5 text-amber-400" />
                <h2 className="text-xl font-bold text-white">Session Summary</h2>
              </div>
              <button
                onClick={() => setShowSessionSummary(false)}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-xs text-slate-400 mt-1">Pinned insights from this conversation</p>
          </div>

          {/* Pinned Messages List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {pinnedMessages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-6">
                <Pin className="w-12 h-12 text-slate-600 mb-3" />
                <p className="text-sm text-slate-400 mb-2">No pinned messages yet</p>
                <p className="text-xs text-slate-500">Click the ⭐ button on AI responses to pin important insights here</p>
              </div>
            ) : (
              pinnedMessages.map((msgId) => {
                const msg = messages.find(m => m.id === msgId);
                if (!msg || msg.type !== 'ai') return null;
                
                const tag = messageTagsMap[msgId];
                const snippet = msg.content.substring(0, 150) + (msg.content.length > 150 ? '...' : '');
                
                return (
                  <div 
                    key={msgId}
                    className="bg-zinc-900/50 border border-white/10 rounded-lg p-4 hover:border-amber-500/30 transition-all cursor-pointer group"
                    onClick={() => {
                      handleScrollToMessage(msgId);
                      setShowSessionSummary(false);
                    }}
                  >
                    {/* Tag Badge */}
                    {tag && (
                      <div className="mb-2">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                          tag === 'decision' ? 'bg-green-500/20 text-green-400 border border-green-500/40' :
                          tag === 'action' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' :
                          'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                        }`}>
                          {tag === 'decision' ? '✅ Decision' : tag === 'action' ? '📝 Action Item' : '💡 Idea'}
                        </span>
                      </div>
                    )}
                    
                    {/* Agent Info */}
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 via-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs">
                        {msg.agent && agentProfiles[msg.agent as keyof typeof agentProfiles] ? (
                          <img 
                            src={agentProfiles[msg.agent as keyof typeof agentProfiles].image}
                            alt={agentProfiles[msg.agent as keyof typeof agentProfiles].name}
                            className="w-full h-full rounded-full object-cover"
                          />
                        ) : '⚡'}
                      </div>
                      <span className="text-xs font-medium text-slate-400">
                        {msg.agent && agentProfiles[msg.agent as keyof typeof agentProfiles] 
                          ? agentProfiles[msg.agent as keyof typeof agentProfiles].name 
                          : 'EPC Agent'}
                      </span>
                    </div>
                    
                    {/* Message Snippet */}
                    <p className="text-xs text-slate-300 line-clamp-3 mb-3">{snippet}</p>
                    
                    {/* Action Buttons */}
                    <div className="flex items-center justify-between pt-2 border-t border-white/5">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleScrollToMessage(msgId);
                          setShowSessionSummary(false);
                        }}
                        className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                        Jump to message
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTogglePin(msgId);
                        }}
                        className="text-xs text-red-400 hover:text-red-300"
                      >
                        Unpin
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Clear All Button */}
          {pinnedMessages.length > 0 && (
            <div className="p-4 border-t border-white/10">
              <button
                onClick={() => {
                  setPinnedMessages([]);
                  localStorage.removeItem('epc-pinned-messages');
                }}
                className="w-full py-2 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm font-medium hover:bg-red-500/30 transition-colors"
              >
                Clear All Pins
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Overlay when session summary open */}
      {showSessionSummary && (
        <div 
          className="fixed inset-0 bg-black/30 z-40"
          onClick={() => setShowSessionSummary(false)}
        />
      )}

      {/* Custom animations - Add to your CSS */}
      <style>{`
        @keyframes gradient-x {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        
        @keyframes scan {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(300%); }
        }
        
        @keyframes scan-horizontal {
          0% { transform: translateX(-100%); opacity: 0; }
          50% { opacity: 1; }
          100% { transform: translateX(100%); opacity: 0; }
        }
        
        @keyframes float-slow {
          0%, 100% { transform: translateY(0px) translateX(0px); }
          50% { transform: translateY(-20px) translateX(10px); }
        }
        
        @keyframes float-medium {
          0%, 100% { transform: translateY(0px) translateX(0px); }
          50% { transform: translateY(-15px) translateX(-10px); }
        }
        
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        @keyframes pulse-slow {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        @keyframes pulse-glow {
          0%, 100% { opacity: 0; }
          50% { opacity: 0.6; }
        }
        
        .animate-gradient-x { animation: gradient-x 15s ease infinite; background-size: 200% 200%; }
        .animate-shimmer { animation: shimmer 3s linear infinite; }
        .animate-scan { animation: scan 3s linear infinite; }
        .animate-scan-horizontal { animation: scan-horizontal 4s linear infinite; }
        .animate-float-slow { animation: float-slow 6s ease-in-out infinite; }
        .animate-float-medium { animation: float-medium 4s ease-in-out infinite; }
        .animate-spin-slow { animation: spin-slow 8s linear infinite; }
        .animate-pulse-slow { animation: pulse-slow 2s ease-in-out infinite; }
        .animate-pulse-glow { animation: pulse-glow 2s ease-in-out infinite; }
        
        @keyframes highlight-flash {
          0%, 100% { background-color: transparent; }
          50% { background-color: rgba(234, 179, 8, 0.2); }
        }
        
        .highlight-flash {
          animation: highlight-flash 2s ease-in-out;
        }
      `}</style>

      {/* ====================================================================
          MESSAGES AREA
          Scrollable container for all chat messages
      ==================================================================== */}
      <div className="flex-1 flex flex-col w-full overflow-hidden bg-zinc-900">
        <ScrollArea ref={scrollAreaRef} className="flex-1 w-full h-full bg-zinc-900">
          <div className={`${
            settings.spacing === 'compact' ? 'p-2 md:p-3 space-y-2' : 
            settings.spacing === 'spacious' ? 'p-6 md:p-10 space-y-8' : 
            'p-4 md:p-6 space-y-4'
          } max-w-[95%] xl:max-w-[1300px] 2xl:max-w-[1400px] mx-auto`}>
            
            {/* Map through all messages and render appropriate bubble */}
            {messages.map((message) => {
              /**
               * Get Timeline Events for AI Messages
               * Each AI message may have associated processing events
               */
              const eventsForMessage = message.type === "ai" 
                ? (messageEvents.get(message.id) || []) 
                : [];
              
              /**
               * Determine if Current Message is Last AI Message
               * Used to show loading state only on the most recent AI response
               */
              const isCurrentMessageTheLastAiMessage = 
                message.type === "ai" && message.id === lastAiMessageId;

              return (
                <div
                  key={message.id}
                  id={`message-${message.id}`}
                  className={`flex ${
                    message.type === "human" ? "justify-end" : "justify-start"
                  }`}
                >
                  {/* Render appropriate message bubble based on type */}
                  {message.type === "human" ? (
                    <div className="relative group max-w-[75%]">
                      {/* Gradient glow behind message */}
                      <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 via-blue-500 to-cyan-500 rounded-3xl blur opacity-30 group-hover:opacity-50 transition-opacity" />
                      {/* Message bubble with gradient background */}
                      <div className="relative bg-gradient-to-r from-indigo-500 via-blue-500 to-cyan-500 rounded-3xl p-5 shadow-2xl">
                        <div className="text-white text-sm leading-relaxed">
                          {message.content}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="relative group w-full">
                      {/* Gradient glow border */}
                      <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 via-blue-500 to-cyan-500 rounded-3xl blur opacity-20 group-hover:opacity-30 transition-opacity" />
                      
                      {/* AI Message Card with glassmorphism */}
                      <div className="relative bg-zinc-900/90 backdrop-blur-xl border-1 border-white rounded-3xl p-6 shadow-2xl">
                        
                        {/* Show timeline ONLY on the last AI message if has events */}
                        {/* COMMENTED OUT - Uncomment to restore timeline
                        {isCurrentMessageTheLastAiMessage && eventsForMessage.length > 0 && (
                          <div className="mb-4">
                            <ActivityTimeline 
                              processedEvents={eventsForMessage}
                              isLoading={isCurrentMessageTheLastAiMessage && isLoading}
                              websiteCount={websiteCount}
                            />
                          </div>
                        )}
                        */}
                        
                        {/* ALWAYS show AI Response Header and Content */}
                        <div className="flex items-center gap-3 mb-4">
                          {/* Agent Avatar with Profile Image */}
                          <div className="relative w-18 h-18 rounded-full shadow-[0_0_30px_rgba(99,102,241,0.5)] ring-2 ring-blue-400/50">
                            {message.agent && agentProfiles[message.agent as keyof typeof agentProfiles] ? (
                              <img 
                                src={agentProfiles[message.agent as keyof typeof agentProfiles].image}
                                alt={agentProfiles[message.agent as keyof typeof agentProfiles].name}
                                className="w-full h-full rounded-full object-cover"
                              />
                            ) : (
                              <div className="w-full h-full rounded-full bg-gradient-to-br from-indigo-500 via-blue-500 to-cyan-500 flex items-center justify-center text-white text-xl">
                                ⚡
                              </div>
                            )}
                          </div>
                          {/* Agent Name */}
                          <div className="flex flex-col">
                            <span className="text-sm font-bold text-white">
                              {message.agent && agentProfiles[message.agent as keyof typeof agentProfiles] 
                                ? agentProfiles[message.agent as keyof typeof agentProfiles].name 
                                : 'EPC Analysis'}
                            </span>
                            <span className="text-xs text-slate-500">AI Agent</span>
                          </div>
                        </div>
                        
                        {/* Message Content */}
                        <div className={`text-slate-300 leading-relaxed ${
                          settings.fontSize === 'small' ? 'text-sm' : 
                          settings.fontSize === 'large' ? 'text-lg' : 
                          'text-base'
                        }`}>
                          {/* DEBUG: Show what's in message */}
                          <div className="mb-3 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-xs backdrop-blur-sm">
                            <div className="flex items-center gap-2 mb-1">
                              <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
                              <span className="text-blue-400 font-semibold tracking-wide">DEBUG INFO</span>
                            </div>
                            <div className="space-y-1 text-slate-300">
                              <div className="flex gap-2">
                                <span className="text-blue-400 font-medium">Length:</span>
                                <span>{message.content?.length || 0}</span>
                              </div>
                              <div className="flex gap-2">
                                <span className="text-blue-400 font-medium">Preview:</span>
                                <span className="truncate">"{message.content?.substring(0, 100) || 'EMPTY'}"</span>
                              </div>
                              <div className="flex gap-2">
                                <span className="text-blue-400 font-medium">Agent:</span>
                                <span className="text-cyan-400">{message.agent || 'none'}</span>
                              </div>
                            </div>
                          </div>
                          
                          <ReactMarkdown components={mdComponents} remarkPlugins={[remarkGfm, remarkBreaks]}>
                            {message.content}
                          </ReactMarkdown>

                          {/* Insights Section (Key Points) */}
                          {highlightsByMessage[message.id] && highlightsByMessage[message.id].length > 0 && (
                            <div className="mt-4 p-3 rounded-xl bg-blue-500/5 border border-blue-500/30 text-xs">
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                                  <span className="text-blue-300 font-semibold tracking-wide">INSIGHTS – KEY POINTS</span>
                                </div>
                                <button
                                  onClick={() =>
                                    setExpandedInsights((prev) => ({
                                      ...prev,
                                      [message.id]: !prev[message.id],
                                    }))
                                  }
                                  className="text-[10px] text-blue-300 hover:text-blue-100 underline-offset-2 hover:underline"
                                >
                                  {expandedInsights[message.id] ? "Hide" : "Show"}
                                </button>
                              </div>
                              {expandedInsights[message.id] && (
                                <ul className="list-disc pl-4 space-y-1 text-slate-200">
                                  {highlightsByMessage[message.id].map((item, idx) => (
                                    <li key={idx}>{item}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          )}

                          {/* Summary Section */}
                          {summaryByMessage[message.id] && (
                            <div className="mt-3 p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/30 text-xs">
                              <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-2">
                                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                  <span className="text-emerald-300 font-semibold tracking-wide">SUMMARY</span>
                                </div>
                                <button
                                  onClick={() =>
                                    setExpandedSummary((prev) => ({
                                      ...prev,
                                      [message.id]: !prev[message.id],
                                    }))
                                  }
                                  className="text-[10px] text-emerald-300 hover:text-emerald-100 underline-offset-2 hover:underline"
                                >
                                  {expandedSummary[message.id] ? "Hide" : "Show"}
                                </button>
                              </div>
                              {expandedSummary[message.id] && (
                                <p className="text-slate-200">
                                  {summaryByMessage[message.id]}
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                        
                        {/* Message Tag Display */}
                        {messageTagsMap[message.id] && (
                          <div className="mb-3">
                            <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
                              messageTagsMap[message.id] === 'decision' ? 'bg-green-500/20 text-green-400 border border-green-500/40' :
                              messageTagsMap[message.id] === 'action' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' :
                              'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                            }`}>
                              {messageTagsMap[message.id] === 'decision' ? '✅ Decision' : 
                               messageTagsMap[message.id] === 'action' ? '📝 Action Item' : 
                               '💡 Idea'}
                              <button
                                onClick={() => handleRemoveTag(message.id)}
                                className="ml-1 hover:opacity-70"
                              >
                                ✕
                              </button>
                            </span>
                          </div>
                        )}

                        {/* ALL ACTION BUTTONS - SINGLE ROW */}
                        <div className="mt-4 flex flex-wrap items-center gap-2">
                          
                          {/* === GROUP 1: PRODUCTIVITY ACTIONS === */}
                          <button
                            onClick={() => handleTogglePin(message.id)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 border rounded-full text-xs transition-all duration-200 ${
                              pinnedMessages.includes(message.id)
                                ? 'bg-amber-500/20 border-amber-500/40 text-amber-400 hover:bg-amber-500/30'
                                : 'bg-white/5 hover:bg-white/10 border-white/10 text-slate-400 hover:text-white'
                            }`}
                          >
                            <Pin className="w-3 h-3" />
                            {pinnedMessages.includes(message.id) ? 'Pinned' : 'Pin'}
                          </button>

                          {!messageTagsMap[message.id] && (
                            <div className="relative">
                              <button 
                                onClick={() => setOpenTagDropdown(openTagDropdown === message.id ? null : message.id)}
                                className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs text-slate-400 hover:text-white transition-all duration-200"
                              >
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                                </svg>
                                Tag
                              </button>
                              {openTagDropdown === message.id && (
                                <div className="absolute left-0 top-full mt-1 z-10 bg-zinc-900 border border-white/20 rounded-lg shadow-2xl overflow-hidden">
                                  <button 
                                    onClick={() => {
                                      handleSetTag(message.id, 'decision');
                                      setOpenTagDropdown(null);
                                    }} 
                                    className="w-full px-3 py-2 text-left text-xs hover:bg-green-500/20 text-green-400 flex items-center gap-2 transition-colors whitespace-nowrap"
                                  >
                                    ✅ Decision
                                  </button>
                                  <button 
                                    onClick={() => {
                                      handleSetTag(message.id, 'action');
                                      setOpenTagDropdown(null);
                                    }} 
                                    className="w-full px-3 py-2 text-left text-xs hover:bg-amber-500/20 text-amber-400 flex items-center gap-2 transition-colors whitespace-nowrap"
                                  >
                                    📝 Action
                                  </button>
                                  <button 
                                    onClick={() => {
                                      handleSetTag(message.id, 'idea');
                                      setOpenTagDropdown(null);
                                    }} 
                                    className="w-full px-3 py-2 text-left text-xs hover:bg-blue-500/20 text-blue-400 flex items-center gap-2 transition-colors whitespace-nowrap"
                                  >
                                    💡 Idea
                                  </button>
                                </div>
                              )}
                            </div>
                          )}

                          <button onClick={() => setCleanViewMessage(message.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs text-slate-400 hover:text-white transition-all duration-200">
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            Clean View
                          </button>

                          {/* Separator */}
                          <div className="h-6 w-px bg-white/10" />

                          {/* === GROUP 2: COPY ACTIONS === */}
                          <button onClick={() => handleCopy(message.content, message.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs text-slate-400 hover:text-white transition-all duration-200">
                            {copiedMessageId === message.id ? (
                              <>
                                <svg className="w-3 h-3 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                <span className="text-green-500">Copied!</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                Copy
                              </>
                            )}
                          </button>

                          <button onClick={() => handleCopyMarkdown(message.content, message.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs text-slate-400 hover:text-white transition-all duration-200">
                            <Copy className="w-3 h-3" />
                            Markdown
                          </button>

                          <button onClick={() => handleCopyPlainText(message.content, message.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs text-slate-400 hover:text-white transition-all duration-200">
                            <Copy className="w-3 h-3" />
                            Text
                          </button>

                          {/* Separator */}
                          <div className="h-6 w-px bg-white/10" />

                          {/* === GROUP 3: DOWNLOAD ACTIONS === */}
                          <button onClick={() => handleDownloadHtml(message.content, message.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs text-slate-400 hover:text-white transition-all duration-200">
                            <Download className="w-3 h-3" />
                            HTML
                          </button>

                          <button onClick={() => handleDownloadPdf(message.content, message.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs text-slate-400 hover:text-white transition-all duration-200">
                            <Download className="w-3 h-3" />
                            PDF
                          </button>

                          <button onClick={() => handleDownloadTxt(message.content, message.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs text-slate-400 hover:text-white transition-all duration-200">
                            <Download className="w-3 h-3" />
                            TXT
                          </button>

                          {/* Separator */}
                          <div className="h-6 w-px bg-white/10" />

                          {/* === GROUP 4: AI ANALYSIS === */}
                          <button onClick={() => handleGenerateHighlights(message.content, message.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/40 rounded-full text-xs text-blue-300 hover:text-blue-100 transition-all duration-200">
                            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                            Highlights
                          </button>

                          <button onClick={() => handleGenerateSummary(message.content, message.id)} className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/40 rounded-full text-xs text-emerald-300 hover:text-emerald-100 transition-all duration-200">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            Summary
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            
            {/* ================================================================
                LOADING INDICATORS
                Multiple conditions for showing "Thinking..." state
            ================================================================ */}
            
            {/* Loading indicator when no AI messages exist yet */}
            {isLoading && !lastAiMessage && messages.some(m => m.type === 'human') && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 text-neutral-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Thinking...</span>
                </div>
              </div>
            )}
            
            {/* Loading indicator when last message is from human */}
            {isLoading && messages.length > 0 && messages[messages.length - 1].type === 'human' && (
              <div className="flex justify-start pl-10 pt-2">
                <div className="flex items-center gap-2 text-neutral-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Thinking...</span>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
      
      {/* ====================================================================
          EPIC INPUT AREA with animations
          Fixed bottom section with text input and controls
      ==================================================================== */}
      <div className={`relative border-t border-white/10 p-3 md:p-4 w-full overflow-hidden ${
        settings.focusMode ? 'bg-zinc-950' : 'bg-black'
      }`}>
        {/* Animated gradient background - Hide in Focus Mode */}
        {!settings.focusMode && (
          <div className="absolute inset-4 bg-gradient-to-r from-blue-500/5 via-cyan-500/5 to-blue-500/5 animate-gradient-x" />
        )}
        
        {/* Scanning line at top */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50 animate-scan-horizontal" />
        
        <div className="max-w-[95%] xl:max-w-[1300px] 2xl:max-w-[1400px] mx-auto relative z-10">
          
          {/* Suggestion Chips - Only show when not loading */}
          {!isLoading && messages.length === 0 && (
            <div className="mb-4 flex flex-wrap gap-3 justify-center animate-fadeInUp">
              <button
                onClick={() => onSubmit("Show me NBOT breakdown by region")}
                className="group relative px-4 py-2 rounded-full bg-zinc-900/50 border border-blue-500/30 hover:border-cyan-400 transition-all duration-300 hover:scale-105"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
                <span className="relative text-sm text-slate-300 group-hover:text-cyan-400 transition-colors flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  NBOT Analysis
                </span>
              </button>

              <button
                onClick={() => onSubmit("Analyze schedule optimization for next week")}
                className="group relative px-4 py-2 rounded-full bg-zinc-900/50 border border-blue-500/30 hover:border-cyan-400 transition-all duration-300 hover:scale-105"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
                <span className="relative text-sm text-slate-300 group-hover:text-cyan-400 transition-colors flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  Schedule Optimization
                </span>
              </button>

              <button
                onClick={() => onSubmit("Check training compliance status")}
                className="group relative px-4 py-2 rounded-full bg-zinc-900/50 border border-blue-500/30 hover:border-cyan-400 transition-all duration-300 hover:scale-105"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
                <span className="relative text-sm text-slate-300 group-hover:text-cyan-400 transition-colors flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Training Compliance
                </span>
              </button>

              <button
                onClick={() => onSubmit("Generate customer overview report")}
                className="group relative px-4 py-2 rounded-full bg-zinc-900/50 border border-blue-500/30 hover:border-cyan-400 transition-all duration-300 hover:scale-105"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-cyan-500/10 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
                <span className="relative text-sm text-slate-300 group-hover:text-cyan-400 transition-colors flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Customer Report
                </span>
              </button>
            </div>
          )}
          
          {/* File Upload Section */}
          {selectedFiles.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {selectedFiles.map((file, index) => (
                <div 
                  key={index}
                  className="group relative"
                >
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 via-blue-500 to-cyan-500 rounded-lg blur opacity-30 group-hover:opacity-50 transition-opacity" />
                  <div className="relative flex items-center gap-2 px-3 py-2 bg-zinc-900 border border-blue-500/30 rounded-lg">
                    <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    <span className="text-sm text-slate-300">{file.name}</span>
                    <span className="text-xs text-slate-500">({(file.size / 1024).toFixed(1)} KB)</span>
                    <button
                      onClick={() => handleRemoveFile(index)}
                      className="ml-2 p-1 hover:bg-red-500/20 rounded transition-colors"
                    >
                      <svg className="w-3 h-3 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
              <button
                onClick={handleClearFiles}
                className="relative group"
              >
                <div className="absolute -inset-0.5 bg-gradient-to-r from-red-500 to-pink-500 rounded-lg blur opacity-30 group-hover:opacity-50 transition-opacity" />
                <div className="relative px-3 py-2 bg-zinc-900 border border-red-500/30 rounded-lg text-sm text-red-400 hover:text-red-300 transition-colors">
                  Clear All
                </div>
              </button>
            </div>
          )}

          {/* Flex Row: Upload Button (Left) + Input (Center) */}
          <div className="flex items-center gap-3">
            
            {/* Hidden File Input */}
            <input
              type="file"
              id="fileUpload"
              multiple
              accept=".pdf,.doc,.docx,.txt,.csv,.xlsx,.xls,.json,.md"
              onChange={handleFileSelect}
              className="hidden"
            />
            
            {/* Upload Button - Icon Only - Left Side */}
            <label
              htmlFor="fileUpload"
              className="relative group cursor-pointer flex-shrink-0"
            >
              <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 via-blue-500 to-cyan-500 rounded-lg blur opacity-30 group-hover:opacity-60 transition-opacity" />
              <div className="relative flex items-center justify-center w-12 h-12 bg-zinc-900 border border-blue-500/30 rounded-lg hover:border-cyan-400 transition-all">
                <svg className="w-5 h-5 text-blue-400 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
              </div>
            </label>
            
            {/* Input Form - Takes Remaining Space */}
            <div className="flex-1">
              <InputForm 
                onSubmit={(query) => {
                  onSubmit(query, selectedFiles.length > 0 ? selectedFiles : undefined);
                  // Clear files after sending
                  setSelectedFiles([]);
                }} 
                isLoading={isLoading} 
                context="chat"
              />
            </div>
          </div>

          {/* File Count Indicator Below */}
          {selectedFiles.length > 0 && (
            <div className="mt-2 text-center">
              <span className="text-xs text-slate-400">
                {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
              </span>
            </div>
          )}
          
          {/* Cancel button shown during loading */}
          {isLoading && (
            <div className="mt-4 flex justify-center">
              <button
                onClick={onCancel}
                className="relative group"
              >
                <div className="absolute -inset-1 bg-gradient-to-r from-red-500 to-pink-500 rounded-lg blur opacity-30 group-hover:opacity-50 transition-opacity" />
                <div className="relative px-6 py-2 bg-zinc-900 border border-red-500/50 rounded-lg text-sm text-red-400 hover:text-red-300 hover:border-red-400 transition-all">
                  Cancel
                </div>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}