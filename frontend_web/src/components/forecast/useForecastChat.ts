import { useCallback, useMemo, useRef, useState } from 'react';
import { v4 as uuid } from 'uuid';
import { createAgent } from '@/components/block/chat/agent';
import {
  panelFromDamPricesResult,
  panelFromPredictionsResult,
  parseToolResultContent,
  type ForecastPanel,
} from '@/components/forecast/panelUtils';

/** A single renderable row in the agent-trace conversation. */
export type ChatTurn =
  | { kind: 'user'; id: string; text: string }
  | { kind: 'agent-text'; id: string; text: string }
  | {
      kind: 'tool-call';
      id: string;
      toolCallId: string;
      name: string;
      args: string;
      result: string | null;
    };

export interface UseForecastChatOptions {
  /** Suffix for the AG-UI thread id (e.g. "workspace" for Panel tab). */
  threadSuffix?: string;
  /** Called when a chart/table panel is materialized from a tool result. */
  onPanelCreated?: (panel: ForecastPanel, toolName: string) => void;
}

export interface UseForecastChat {
  turns: ChatTurn[];
  panels: ForecastPanel[];
  liveAgentText: string | null;
  isRunning: boolean;
  isThinking: boolean;
  error: string | null;
  sendMessage: (message: string) => Promise<void>;
  clear: () => void;
}

/**
 * Minimal chat controller for the Forecast Assistant. Instantiates an AG-UI
 * HttpAgent pointed at the backend chat endpoint, sends a user message, and
 * accumulates streamed text + tool-call/result events into an ordered list of
 * renderable turns matching the design's AGENT / YOU / TOOL trace.
 */
export function useForecastChat(options: UseForecastChatOptions = {}): UseForecastChat {
  const { threadSuffix, onPanelCreated } = options;
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [panels, setPanels] = useState<ForecastPanel[]>([]);
  const [liveAgentText, setLiveAgentText] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // One agent (thread) per mounted conversation.
  const threadIdRef = useRef<string>(threadSuffix ? `${uuid()}-${threadSuffix}` : uuid());
  const agentRef = useRef<ReturnType<typeof createAgent> | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  const getAgent = useCallback(() => {
    if (!agentRef.current) {
      agentRef.current = createAgent({ threadId: threadIdRef.current });
    }
    return agentRef.current;
  }, []);

  const clear = useCallback(() => {
    unsubscribeRef.current?.();
    unsubscribeRef.current = null;
    agentRef.current = null;
    threadIdRef.current = threadSuffix ? `${uuid()}-${threadSuffix}` : uuid();
    setTurns([]);
    setPanels([]);
    setLiveAgentText(null);
    setIsRunning(false);
    setIsThinking(false);
    setError(null);
  }, []);

  const sendMessage = useCallback(
    async (message: string) => {
      const text = message.trim();
      if (!text || isRunning) return;

      const agent = getAgent();
      setError(null);
      setIsRunning(true);
      setIsThinking(true);
      setLiveAgentText(null);

      const messageId = uuid();

      // Add the user's turn immediately.
      setTurns(prev => [...prev, { kind: 'user', id: messageId, text }]);

      // Only send the new user message — the backend persists it and rebuilds
      // full conversation history from storage before invoking the agent.
      agent.messages = [{ id: messageId, role: 'user', content: text }];

      unsubscribeRef.current?.();
      const { unsubscribe } = agent.subscribe({
        onTextMessageStartEvent() {
          setIsThinking(false);
          setLiveAgentText('');
        },
        onTextMessageContentEvent({ event, textMessageBuffer }) {
          setLiveAgentText(textMessageBuffer + event.delta);
        },
        onTextMessageEndEvent({ textMessageBuffer }) {
          const finalText = textMessageBuffer;
          setLiveAgentText(null);
          if (finalText && finalText.trim()) {
            setTurns(prev => [...prev, { kind: 'agent-text', id: uuid(), text: finalText }]);
          }
        },
        onToolCallStartEvent() {
          setIsThinking(false);
        },
        onToolCallEndEvent({ event, toolCallName, toolCallArgs }) {
          setTurns(prev => [
            ...prev,
            {
              kind: 'tool-call',
              id: uuid(),
              toolCallId: event.toolCallId,
              name: toolCallName,
              args: safeStringify(toolCallArgs),
              result: null,
            },
          ]);
        },
        onToolCallResultEvent({ event }) {
          setTurns(prev => {
            const matching = prev.find(
              t => t.kind === 'tool-call' && t.toolCallId === event.toolCallId
            );
            if (matching?.kind === 'tool-call' && matching.name === 'get_dam_prices') {
              const panel = panelFromDamPricesResult(
                parseToolResultContent(event.content),
                uuid().slice(0, 6)
              );
              if (panel) {
                const withTool = { ...panel, toolName: 'get_dam_prices' };
                setPanels(p => [...p, withTool]);
                onPanelCreated?.(withTool, 'get_dam_prices');
              }
            }
            if (matching?.kind === 'tool-call' && matching.name === 'predict_dam_prices') {
              const panel = panelFromPredictionsResult(
                parseToolResultContent(event.content),
                uuid().slice(0, 6)
              );
              if (panel) {
                const withTool = { ...panel, toolName: 'predict_dam_prices' };
                setPanels(p => [...p, withTool]);
                onPanelCreated?.(withTool, 'predict_dam_prices');
              }
            }
            return prev.map(t =>
              t.kind === 'tool-call' && t.toolCallId === event.toolCallId
                ? { ...t, result: formatResult(event.content) }
                : t
            );
          });
        },
        onRunFinishedEvent() {
          setIsRunning(false);
          setIsThinking(false);
          setLiveAgentText(null);
          unsubscribe();
          unsubscribeRef.current = null;
        },
        onRunErrorEvent({ event }) {
          setError(event.message || 'The agent run failed.');
          setIsRunning(false);
          setIsThinking(false);
          setLiveAgentText(null);
          unsubscribe();
          unsubscribeRef.current = null;
        },
      });
      unsubscribeRef.current = () => {
        unsubscribe();
        agent.abortController.abort();
      };

      try {
        await agent.runAgent({ tools: [] });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to reach the agent.');
        setIsRunning(false);
        setIsThinking(false);
        setLiveAgentText(null);
      }
    },
    [getAgent, isRunning, onPanelCreated]
  );

  return useMemo(
    () => ({
      turns,
      panels,
      liveAgentText,
      isRunning,
      isThinking,
      error,
      sendMessage,
      clear,
    }),
    [turns, panels, liveAgentText, isRunning, isThinking, error, sendMessage, clear]
  );
}

function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function formatResult(content: string): string {
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return content;
  }
}
