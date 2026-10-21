import React, { useState, useRef, useEffect } from 'react';
import {
  Terminal,
  Send,
  X,
  Bot,
  User,
  Sparkles,
  HelpCircle,
} from 'lucide-react';
import { storage } from '../services/storage';

interface TelegramBotModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRefreshData: () => void;
}

interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  timestamp: string;
}

export const TelegramBotModal: React.FC<TelegramBotModalProps> = ({
  isOpen,
  onClose,
  onRefreshData,
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-0',
      sender: 'bot',
      text: '🤖 <b>Job Agent Telegram Supervisor Online</b>\nConnected to autonomous pipeline loops.\n\nType <code>/help</code> or pick a quick command below:',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!isOpen) return null;

  const handleCommand = (rawInput: string) => {
    const trimmed = rawInput.trim();
    if (!trimmed) return;

    const userMsg: Message = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text: trimmed,
      timestamp: new Date().toLocaleTimeString(),
    };

    const parts = trimmed.split(/\s+/);
    const cmd = parts[0].toLowerCase();
    const args = parts.slice(1).join(' ');

    let replyText = '';

    switch (cmd) {
      case '/help':
      case '/start':
        replyText =
          '<b>Supported Telegram Commands:</b>\n' +
          '• <code>/jobs</code> - Top 10 discovered jobs with match scores\n' +
          '• <code>/pending</code> - Applications in READY / MANUAL_REVIEW\n' +
          '• <code>/applied</code> - Submitted applications\n' +
          '• <code>/interviews</code> - Interview tracking list\n' +
          '• <code>/rejected</code> - Filtered & rejected applications\n' +
          '• <code>/stats</code> - 24-hour pipeline throughput & rates\n' +
          '• <code>/apply &lt;id&gt;</code> - Approve application for submission\n' +
          '• <code>/skip &lt;id&gt;</code> - Skip application\n' +
          '• <code>/pause</code> - Pause autonomous worker loops\n' +
          '• <code>/resume</code> - Resume autonomous worker loops\n' +
          '• <code>/profile</code> - View candidate profile facts\n' +
          '• <code>/answers</code> - Browse application answer bank\n' +
          '• <code>/preferences</code> - Remote & compensation settings';
        break;

      case '/jobs':
      case '/today': {
        const jobs = storage.getJobs().slice(0, 5);
        if (jobs.length === 0) {
          replyText = 'No jobs discovered yet.';
        } else {
          replyText = jobs
            .map((j) => {
              const match = storage.getJobMatch(j.id);
              return (
                `💼 <b>${j.title}</b> at <b>${j.company}</b>\n` +
                `Score: <code>${match?.match_score || 0}/100</code> | Source: <i>${j.source}</i>\n` +
                `Location: ${j.location}\n` +
                `App ID: <code>app-${j.id.replace('job-', '')}</code>`
              );
            })
            .join('\n\n');
        }
        break;
      }

      case '/pending': {
        const apps = storage.getApplications().filter((a) => a.state === 'READY' || a.state === 'MANUAL_REVIEW');
        if (apps.length === 0) {
          replyText = 'No pending applications requiring approval.';
        } else {
          replyText =
            '<b>Pending Applications for Approval:</b>\n\n' +
            apps
              .map(
                (a) =>
                  `• <code>${a.id}</code> [${a.state}]\nJob ID: ${a.job_id}\nUse <code>/apply ${a.id}</code> to submit`
              )
              .join('\n\n');
        }
        break;
      }

      case '/applied': {
        const apps = storage.getApplications().filter((a) => a.state === 'SUBMITTED');
        if (apps.length === 0) {
          replyText = 'No applications submitted yet.';
        } else {
          replyText =
            '<b>Submitted Applications:</b>\n\n' +
            apps.map((a) => `• <code>${a.id}</code> | Job: ${a.job_id} | Date: ${a.submitted_at || 'Recent'}`).join('\n');
        }
        break;
      }

      case '/interviews': {
        const apps = storage.getApplications().filter((a) => a.state === 'INTERVIEW');
        if (apps.length === 0) {
          replyText = 'No active interviews currently.';
        } else {
          replyText =
            '<b>🎉 Scheduled Interviews:</b>\n\n' +
            apps.map((a) => `• <code>${a.id}</code> | Job: ${a.job_id}`).join('\n');
        }
        break;
      }

      case '/rejected': {
        const apps = storage
          .getApplications()
          .filter((a) => ['REJECTED_BY_FILTER', 'LOW_MATCH', 'SUBMISSION_FAILED'].includes(a.state));
        replyText =
          '<b>Filtered / Terminated Applications:</b>\n\n' +
          (apps.length === 0
            ? 'None'
            : apps
                .slice(0, 6)
                .map((a) => `• <code>${a.id}</code>: ${a.state} (${a.failure_reason || 'N/A'})`)
                .join('\n'));
        break;
      }

      case '/stats': {
        const s = storage.getDailyStats();
        replyText =
          '<b>📊 24-Hour Autonomous Stats:</b>\n' +
          `• Discovered: ${s.jobs_discovered}\n` +
          `• High Match (≥70): ${s.high_match}\n` +
          `• Applications Prepared: ${s.applications}\n` +
          `• Submitted: ${s.submitted}\n` +
          `• Failed: ${s.failed}\n` +
          `• Interviews: ${s.interviews}\n` +
          `• Offers: ${s.offers}\n` +
          `• Interview Conversion: ${(s.interview_rate * 100).toFixed(1)}%`;
        break;
      }

      case '/apply': {
        if (!args) {
          replyText = 'Usage: <code>/apply &lt;application_id&gt;</code>\nExample: <code>/apply app-stripe-001</code>';
        } else {
          try {
            const updated = storage.transitionApplication(
              args,
              'SUBMITTED',
              'Approved via Telegram command /apply'
            );
            replyText = `✅ <b>Approved & Submitted:</b> <code>${updated.id}</code>\nJob ID: ${updated.job_id}\nState transitioned to SUBMITTED.`;
            onRefreshData();
          } catch (e: any) {
            replyText = `❌ Error: ${e.message}`;
          }
        }
        break;
      }

      case '/skip': {
        if (!args) {
          replyText = 'Usage: <code>/skip &lt;application_id&gt;</code>';
        } else {
          try {
            const updated = storage.transitionApplication(
              args,
              'REJECTED_BY_FILTER',
              'Skipped via Telegram command /skip'
            );
            replyText = `⚠️ <b>Skipped:</b> <code>${updated.id}</code>`;
            onRefreshData();
          } catch (e: any) {
            replyText = `❌ Error: ${e.message}`;
          }
        }
        break;
      }

      case '/pause': {
        storage.setSystemPaused(true);
        replyText = '⏸️ <b>System Paused.</b> Autonomous discovery and application loops are paused.';
        onRefreshData();
        break;
      }

      case '/resume': {
        storage.setSystemPaused(false);
        replyText = '▶️ <b>System Resumed.</b> All 6 supervision loops active.';
        onRefreshData();
        break;
      }

      case '/profile': {
        const p = storage.getProfile();
        replyText =
          `👤 <b>${p.full_name}</b>\n` +
          `Email: ${p.email}\n` +
          `Location: ${p.location}\n` +
          `Remote: ${p.remote_ok ? 'Yes' : 'No'} | Nigeria Eligible: ${p.nigeria_eligible ? 'Yes' : 'No'}\n` +
          `Skills: ${p.skills.slice(0, 8).join(', ')}`;
        break;
      }

      case '/answers': {
        const answers = storage.getAnswers().slice(0, 4);
        replyText =
          '<b>Candidate Answer Bank Snippets:</b>\n\n' +
          answers
            .map((a) => `[${a.category.toUpperCase()}]\nQ: ${a.question}\nA: ${a.answer.slice(0, 100)}...`)
            .join('\n\n');
        break;
      }

      case '/preferences': {
        const p = storage.getProfile();
        replyText =
          '<b>Operator Candidate Preferences:</b>\n' +
          `• Remote: ${p.remote_ok}\n` +
          `• Min Salary: $${p.min_salary?.toLocaleString()} ${p.currency}\n` +
          `• Target Roles: ${p.preferred_roles.join(', ')}\n` +
          `• Availability: ${p.availability}`;
        break;
      }

      default:
        replyText = `❓ Unknown command: <code>${cmd}</code>. Type <code>/help</code> for available commands.`;
        break;
    }

    const botMsg: Message = {
      id: `bot-${Date.now()}`,
      sender: 'bot',
      text: replyText,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg, botMsg]);
    setInput('');
  };

  const quickCommands = [
    '/jobs',
    '/pending',
    '/stats',
    '/interviews',
    '/pause',
    '/resume',
    '/profile',
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full h-[650px] flex flex-col shadow-2xl overflow-hidden">
        {/* Terminal Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-cyan-950 border border-cyan-800/60 flex items-center justify-center text-cyan-400">
              <Terminal className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-sm">Telegram Bot CLI Surface</span>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                Ported from apps/telegram/commands.py
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Message History */}
        <div className="flex-1 p-5 overflow-y-auto space-y-4 font-mono text-xs">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex items-start gap-2.5 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {m.sender === 'bot' && (
                <div className="w-6 h-6 rounded-lg bg-blue-950 border border-blue-800 text-blue-400 flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-3.5 h-3.5" />
                </div>
              )}

              <div
                className={`max-w-[85%] p-3.5 rounded-2xl leading-relaxed whitespace-pre-wrap ${
                  m.sender === 'user'
                    ? 'bg-blue-600 text-white rounded-tr-none'
                    : 'bg-slate-950 text-slate-200 border border-slate-800 rounded-tl-none'
                }`}
                dangerouslySetInnerHTML={{ __html: m.text }}
              />

              {m.sender === 'user' && (
                <div className="w-6 h-6 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-3.5 h-3.5" />
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Command Chips */}
        <div className="px-5 py-2 border-t border-slate-800/80 bg-slate-950/60 flex flex-wrap gap-1.5">
          <span className="text-[10px] text-slate-500 font-mono self-center mr-1">Quick:</span>
          {quickCommands.map((cmd) => (
            <button
              key={cmd}
              onClick={() => handleCommand(cmd)}
              className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-all cursor-pointer"
            >
              {cmd}
            </button>
          ))}
        </div>

        {/* Command Input Bar */}
        <div className="p-4 border-t border-slate-800 bg-slate-950">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleCommand(input);
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Enter Telegram command (/help, /jobs, /apply <id>, /stats)..."
              className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              className="p-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl transition-all cursor-pointer shrink-0 shadow-sm"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
