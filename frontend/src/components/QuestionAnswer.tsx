import { useState } from 'react';
import { DocumentQuestionResponse } from '../types';

interface QuestionAnswerProps {
  question: string;
  answer: DocumentQuestionResponse | null;
  isLoading?: boolean;
  onAskFollowup?: (question: string) => void;
}

export default function QuestionAnswer({
  question,
  answer,
  isLoading,
  onAskFollowup,
}: QuestionAnswerProps) {
  const [followupQuestion, setFollowupQuestion] = useState('');

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg p-6 border border-gray-200">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
        </div>
      </div>
    );
  }

  if (!answer) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg p-6 border border-gray-200 space-y-6">
      {/* Question */}
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <p className="font-semibold text-gray-900">{question}</p>
      </div>

      {/* Answer */}
      <div className="prose max-w-none">
        <p className="text-gray-700 whitespace-pre-wrap">{answer.answer}</p>
        {answer.confidence > 0 && (
          <p className="text-sm text-gray-500 mt-2">
            Confidence: {Math.round(answer.confidence * 100)}%
          </p>
        )}
      </div>

      {/* Sources */}
      {answer.sources && answer.sources.length > 0 && (
        <div className="border-t border-gray-200 pt-4">
          <h4 className="font-semibold text-gray-900 mb-3">📚 Sources:</h4>
          <div className="space-y-2">
            {answer.sources.map((source, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-gray-500">📄</span>
                <div>
                  <p className="font-medium text-gray-900">
                    {source.document_title}
                    {source.company_name && ` - ${source.company_name}`}
                  </p>
                  {source.chunk_text && (
                    <p className="text-gray-600 text-xs mt-1 line-clamp-2">
                      {source.chunk_text}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Followup Question */}
      {onAskFollowup && (
        <div className="border-t border-gray-200 pt-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (followupQuestion.trim()) {
                onAskFollowup(followupQuestion);
                setFollowupQuestion('');
              }
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={followupQuestion}
              onChange={(e) => setFollowupQuestion(e.target.value)}
              placeholder="Ask a followup question..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-dawn focus:border-dawn"
            />
            <button
              type="submit"
              className="px-6 py-2 bg-dawn text-white rounded-lg hover:bg-dawn/90 font-medium"
            >
              Ask
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

