// ============================================================================
// IMPORTS SECTION
// ============================================================================
/**
 * React Hooks Imports
 * - useState: Manages local component state for the input value
 * - useRef: Creates a reference to the textarea DOM element for focus control
 * - useEffect: Handles side effects like auto-focusing on component mount
 */
import { useState, useRef, useEffect } from "react";

/**
 * UI Component Imports
 * - Button: Reusable button component from the UI library
 * - Textarea: Multi-line text input component with auto-resize capabilities
 */
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

/**
 * Icon Imports from Lucide React
 * - Loader2: Spinning loader icon shown during loading state
 * - Send: Paper plane icon for the submit button
 */
import { Loader2, Send } from "lucide-react";

// ============================================================================
// TYPESCRIPT INTERFACE
// ============================================================================
/**
 * InputFormProps Interface
 * Defines the contract for props passed to the InputForm component
 * 
 * @param onSubmit - Callback function that receives the user's input string
 *                   Called when form is submitted with valid input
 * @param isLoading - Boolean flag indicating if the system is processing
 *                    Disables input and shows loading spinner when true
 * @param context - Optional context to customize behavior and placeholder text
 *                  'homepage': Initial landing page context
 *                  'chat': Active chat conversation context
 */
interface InputFormProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
  context?: 'homepage' | 'chat'; // Add new context prop
}

// ============================================================================
// INPUT FORM COMPONENT
// ============================================================================
/**
 * InputForm Component
 * 
 * A reusable form component that provides a text input area and submit button
 * for users to interact with the APEX AI Agent system.
 * 
 * Features:
 * - Auto-focus on mount for immediate user interaction
 * - Enter key submission (Shift+Enter for new lines)
 * - Loading state with spinner animation
 * - Context-aware placeholder text
 * - Automatic input clearing after submission
 * - Disabled state during loading to prevent multiple submissions
 */
export function InputForm({ 
  onSubmit, 
  isLoading, 
  context = 'homepage'  // Default to homepage context if not specified
}: InputFormProps) {
  
  // ========================================================================
  // STATE MANAGEMENT
  // ========================================================================
  /**
   * Local State: inputValue
   * Stores the current text content of the textarea
   * Controlled component pattern - React controls the input value
   */
  const [inputValue, setInputValue] = useState("");
  
  /**
   * Ref: textareaRef
   * Direct reference to the textarea DOM element
   * Used to programmatically focus the textarea on component mount
   * Type: HTMLTextAreaElement for TypeScript type safety
   */
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ========================================================================
  // LIFECYCLE EFFECTS
  // ========================================================================
  /**
   * Auto-Focus Effect
   * Runs once when component mounts (empty dependency array [])
   * Automatically focuses the textarea so users can start typing immediately
   * Improves UX by eliminating the need to click the input field
   */
  useEffect(() => {
    // Check if ref is attached to prevent null reference errors
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []); // Empty array means this effect runs only once on mount

  // ========================================================================
  // EVENT HANDLERS
  // ========================================================================
  /**
   * Form Submit Handler
   * Processes form submission from both button click and Enter key press
   * 
   * @param e - React form event
   * 
   * Validation checks:
   * 1. Input must not be empty (after trimming whitespace)
   * 2. System must not be currently loading (prevents double submission)
   * 
   * Actions on valid submission:
   * 1. Calls parent's onSubmit with trimmed input
   * 2. Clears the input field for next query
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault(); // Prevent default form submission (page refresh)
    
    // Validate input: must have content and not be loading
    if (inputValue.trim() && !isLoading) {
      onSubmit(inputValue.trim()); // Send trimmed input to parent
      setInputValue(""); // Clear input field after submission
    }
  };

  /**
   * Keyboard Event Handler
   * Enables Enter key submission while preserving Shift+Enter for new lines
   * 
   * @param e - React keyboard event from textarea
   * 
   * Behavior:
   * - Enter alone: Submit the form
   * - Shift+Enter: Add a new line (default textarea behavior)
   * 
   * This pattern is common in chat applications (Slack, Discord, etc.)
   */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Check if Enter was pressed without Shift modifier
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); // Prevent newline insertion
      handleSubmit(e); // Submit the form
    }
    // If Shift+Enter, allow default behavior (new line)
  };

  // ========================================================================
  // DYNAMIC CONTENT
  // ========================================================================
  /**
   * Context-Aware Placeholder Text
   * Changes the input placeholder based on where the component is used
   * 
   * - Homepage: "Connect with..." - First interaction, establishing connection
   * - Chat: "Interact with..." - Ongoing conversation, continuous interaction
   * 
   * Both mention "Chief AI Agent Jordan" to personalize the experience
   */
  const placeholderText =
    context === 'chat'
      ? "Welcome to the Future ... ✨"
      : "Connect with our Team here ... 👉";

  // ========================================================================
  // COMPONENT RENDER
  // ========================================================================
  return (
    <form onSubmit={handleSubmit} className="relative">
      {/* Gradient border glow - brightens when typing */}
      <div 
        className="absolute -inset-0.5 bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 rounded-3xl blur transition-opacity duration-300"
        style={{ opacity: inputValue.length > 0 ? 0.4 : 0.2 }}
      />
      
      {/* Main input container with glassmorphism */}
      <div className="relative bg-zinc-900/90 backdrop-blur-xl border border-white/10 rounded-3xl p-4 shadow-2xl">
        <div className="flex items-center gap-4">
          {/* Text Input */}
          <Textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholderText}
            rows={1}
            className="flex-1 bg-transparent border-none outline-none text-white placeholder-slate-500 text-sm resize-none focus:ring-0"
          />
          
          {/* Gradient Send Button */}
          <button 
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="relative group flex-shrink-0"
          >
            {/* Button glow effect */}
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full blur opacity-50 group-hover:opacity-75 transition-opacity" />
            
            {/* Button main */}
            <div 
              className="relative w-11 h-11 rounded-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg transition-all duration-200"
              style={{
                opacity: isLoading || !inputValue.trim() ? 0.5 : 1,
                cursor: isLoading || !inputValue.trim() ? 'not-allowed' : 'pointer'
              }}
              onMouseEnter={(e) => {
                if (!isLoading && inputValue.trim()) {
                  e.currentTarget.style.transform = 'scale(1.05)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
              }}
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 text-white animate-spin" />
              ) : (
                <Send className="w-4 h-4 text-white" />
              )}
            </div>
          </button>
        </div>
      </div>
    </form>
  );
}