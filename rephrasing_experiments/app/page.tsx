'use client';

import './globals.css';
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { Container, Typography, Button, Card, CardContent, Box } from '@mui/material';
import InstructionsDialog from './components/InstructionsDialog';
import QuestionCard from './components/QuestionCard';
import questions from './data/questions.json';

// Utility function to shuffle an array
const shuffleArray = (array: any[]) => {
  return array
    .map(value => ({ value, sort: Math.random() }))
    .sort((a, b) => a.sort - b.sort)
    .map(({ value }) => value);
};

export default function Home() {
  const [shuffledQuestions, setShuffledQuestions] = useState<any[]>([]);
  const [answers, setAnswers] = useState<Record<number, { 
    posA: string,
    timeSpent: number,
    subAnswers: Record<number, string>,
    explanation?: string
  }>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState('');
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [showInstructions, setShowInstructions] = useState(true);
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now());

  const searchParams = useSearchParams();
  const participantID = searchParams.get('PROLIFIC_PID');

  // Shuffle questions on component mount
  useEffect(() => {
    const shuffled = shuffleArray(questions).map((question, index) => {
      // Shuffle display order of texts
      const shuffledTexts = shuffleArray([
        { type: 'templated', text: question.templated },
        { type: 'rephrased', text: question.rephrased }
      ]);
      return {
        ...question,
        displayedId: index + 1,
        texts: shuffledTexts,
      };
    });
    setShuffledQuestions(shuffled);
  }, []);

  const currentQuestion = shuffledQuestions[currentQuestionIndex];

  const handleInstructionsClose = () => {
    setShowInstructions(false);
    setQuestionStartTime(Date.now());
  };

  const handleInstructionsOpen = () => {
    const timeSpent = Date.now() - questionStartTime;
    const currentQuestionId = shuffledQuestions[currentQuestionIndex]?.id;
    console.log('Current Question ID:', currentQuestionId);
    console.log('Incremented time:', timeSpent / 1000);
    setAnswers(prev => {
      const prevTime = prev[currentQuestionId]?.timeSpent || 0;
      console.log('Total time:', prevTime + timeSpent / 1000);
      return {
        ...prev,
        [currentQuestionId]: {
          ...prev[currentQuestionId],
          timeSpent: prevTime + timeSpent / 1000,
        }
      };
    });
    
    setShowInstructions(true);
  };

  const handleAnswerChange = (
    questionId: number, 
    posA: string, 
    subQuestionId: number, 
    chosenValue: string, 
    explanation?: string
  ) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: {
        ...prev[questionId],
        posA,
        timeSpent: prev[questionId]?.timeSpent || 0,
        subAnswers: {
          ...prev[questionId]?.subAnswers,
          [subQuestionId]: chosenValue,
        },
        ...(explanation && subQuestionId === 3 && chosenValue === 'No' ? { explanation } : {})
      },
    }));
  };

  const isCurrentQuestionAnswered = () => {
    const currentQuestionId = shuffledQuestions[currentQuestionIndex]?.id;
    const currentAnswers = answers[currentQuestionId];

    return currentAnswers && currentAnswers.subAnswers &&
           currentAnswers.subAnswers[1] !== undefined && 
           currentAnswers.subAnswers[2] !== undefined && 
           currentAnswers.subAnswers[3] !== undefined;
  };

  const handleNextQuestion = () => {
    // Calculate time spent on the current question during this session
    const timeSpent = Date.now() - questionStartTime;
    const currentQuestionId = shuffledQuestions[currentQuestionIndex]?.id;
    console.log('Current Question ID:', currentQuestionId);
    console.log('Incremented time:', timeSpent / 1000);

    setAnswers(prev => {
      const prevTime = prev[currentQuestionId]?.timeSpent || 0;
      console.log('Total time:', prevTime + timeSpent / 1000);
      return {
        ...prev,
        [currentQuestionId]: {
          ...prev[currentQuestionId],
          timeSpent: prevTime + timeSpent / 1000, // Increment time
        }
      };
    });

    if (currentQuestionIndex < shuffledQuestions.length - 1) {
      // Move to the next question and reset the timer
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setQuestionStartTime(Date.now());
    }
  };
  
  const handlePreviousQuestion = () => {
    // Calculate time spent on the current question during this session
    const timeSpent = Date.now() - questionStartTime;
    const currentQuestionId = shuffledQuestions[currentQuestionIndex]?.id;
    console.log('Current Question ID:', currentQuestionId);
    console.log('Incremented time:', timeSpent / 1000);
    setAnswers(prev => {
      const prevTime = prev[currentQuestionId]?.timeSpent || 0;
      console.log('Total time:', prevTime + timeSpent / 1000);
      return {
        ...prev,
        [currentQuestionId]: {
          ...prev[currentQuestionId],
          timeSpent: prevTime + timeSpent / 1000, // Increment time
        }
      };
    });

    if (currentQuestionIndex > 0) {
      // Move to the previous question and reset the timer
      setCurrentQuestionIndex(currentQuestionIndex - 1);
      setQuestionStartTime(Date.now());
    }
  };

  const areAllQuestionsAnswered = () => {
    return shuffledQuestions.every(question => {
      const qAnswers = answers[question.id];
      return qAnswers && qAnswers.subAnswers &&
             qAnswers.subAnswers[1] !== undefined &&
             qAnswers.subAnswers[2] !== undefined &&
             qAnswers.subAnswers[3] !== undefined;
    });
  };

  const handleSubmit = async () => {
    if (!areAllQuestionsAnswered()) return;
  
    // Save the time spent on the final question
    const timeSpent = Date.now() - questionStartTime;
    const currentQuestionId = shuffledQuestions[currentQuestionIndex]?.id;
    const updatedAnswers = {
      ...answers,
      [currentQuestionId]: {
        ...answers[currentQuestionId],
        timeSpent: (answers[currentQuestionId]?.timeSpent || 0) + timeSpent / 1000,
      }
    };
    const submissionData = {
      participantID: participantID || 'unknown', // Add participantID from search params
      answers: updatedAnswers,
    };
  
    setIsSubmitting(true);
    try {
      const response = await fetch('/api/saveResponse', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(submissionData),
      });
  
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const result = await response.json();
      setSubmitMessage(result.message);
  
      localStorage.setItem('surveySubmitted', 'true');
      setHasSubmitted(true);
    } catch (error) {
      console.error('Error submitting response:', error);
      setSubmitMessage('Failed to save response');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Check localStorage for submission flag on component mount
  useEffect(() => {
    const submissionStatus = localStorage.getItem('surveySubmitted');
    if (submissionStatus === 'true') {
      setHasSubmitted(true);
    }
  }, []);

  const handleReset = () => {
    localStorage.removeItem('surveySubmitted');
    setHasSubmitted(false);
  };

  return (
    <Container>
      <InstructionsDialog
        open={showInstructions}
        onClose={handleInstructionsClose}
      />

      {!hasSubmitted ? (
        <>
          <Card variant="outlined" sx={{ marginTop: 2, marginBottom: 2 }}>
            <CardContent>
              <Typography variant="h4" component="div" gutterBottom>
                Comparison of Diet-Coaching Chatbot Responses
              </Typography>
              <Typography variant="body1" component="div" sx={{ marginBottom: 1 }}>
                <b>Please carefully read each of the response options provided by a diet-coaching chatbot and answer the questions comparing these responses.</b>
              </Typography>
              <Button
                variant="outlined"
                color="secondary"
                onClick={handleInstructionsOpen}
              >
                Show instructions
              </Button>
            </CardContent>
          </Card>

          {/* Display the current question */}
          {currentQuestion && (
            <QuestionCard
              key={currentQuestion.id}
              questionId={currentQuestion.id} // Original question ID
              displayId={currentQuestion.displayedId} // Display consecutive IDs
              history={currentQuestion.history} // Conversation history before texts
              texts={currentQuestion.texts} // The shuffled texts with type
              prevAnswers={answers[currentQuestion.id] || {}} // Pass previously selected answers
              onAnswer={handleAnswerChange} // Updated handler
            />
          )}

          {/* Navigation buttons */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <Button
              variant="outlined"
              color="secondary"
              onClick={handlePreviousQuestion}
              disabled={currentQuestionIndex === 0}
            >
              Previous
            </Button>
            {currentQuestionIndex < shuffledQuestions.length - 1 ? (
              <Button
                variant="contained"
                color="primary"
                onClick={handleNextQuestion}
                disabled={!isCurrentQuestionAnswered()}
              >
                Next
              </Button>
            ) : (
              <Button
                variant="contained"
                color="primary"
                onClick={handleSubmit}
                disabled={!areAllQuestionsAnswered() || isSubmitting}
              >
                {isSubmitting ? 'Submitting...' : 'Submit'}
              </Button>
            )}
          </Box>
        </>
      ) : (
        <>
          <Typography variant="h6" color="textPrimary" gutterBottom sx={{ marginTop: 4 }}>
            Thank you! Your response has been recorded.
          </Typography>
          <Typography variant="h6" color="textPrimary">
            To complete your submission, return to Prolific via the button below.
          </Typography>
          <Button
            variant="contained"
            color="primary"
            onClick={() => window.location.href = 'https://app.prolific.com/submissions/complete?cc=C10SMSDU'}
            sx={{ marginTop: 2 }}
          >
            Return to Prolific
          </Button>
          {/* <Button
            variant="outlined"
            color="secondary"
            onClick={handleReset}
          >
            Reset Survey
          </Button> */}
        </>
      )}
      {submitMessage && (
        <Typography variant="body1" color="textSecondary" gutterBottom>
          {submitMessage}
        </Typography>
      )}
    </Container>
  );
}
