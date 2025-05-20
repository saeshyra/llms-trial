import React, { useState, useEffect } from "react";
import { Card, CardContent, Typography, RadioGroup, FormControlLabel, Radio, Box, Grid, TextField } from "@mui/material";
import Image from "next/image"
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";

type QuestionCardProps = {
  questionId: number;  // Original question ID
  displayId: number;   // Consecutive display ID
  history: string[][];
  texts: { type: string; text: string[] }[]; // List of shuffled texts with their types (templated or rephrased)
  prevAnswers: { 
    posA: string,
    timeSpent: number,
    subAnswers: Record<number, string>,
    explanation?: string
  }
  onAnswer: (questionId: number, posA: string, subQuestionId: number, chosenValue: string, explanation?: string) => void;
};

const QuestionCard = ({ questionId, displayId, history, texts, prevAnswers, onAnswer }: QuestionCardProps) => {
  const [showExplanation, setShowExplanation] = useState(false);  // Track whether "No" was selected
  const [explanationText, setExplanationText] = useState(""); // Track the text in the explanation box
  const [selectedAnswers, setSelectedAnswers] = useState(prevAnswers.subAnswers || {1: "", 2: "", 3: ""});

  // Shuffle Response A and Response B labels
  const shuffledOptions = texts.map((textItem, idx) => ({
    label: `Response ${String.fromCharCode(65 + idx)}`, // Response A, B, ...
    type: textItem.type, // templated or rephrased
    text: textItem.text, // List of strings (messages)
  }));

  // Determine what type is at position A
  const posA = shuffledOptions[0].type; // The first option in the shuffled list is Response A

  useEffect(() => {
    setSelectedAnswers({
      1: prevAnswers.subAnswers?.[1] || "",
      2: prevAnswers.subAnswers?.[2] || "",
      3: prevAnswers.subAnswers?.[3] || "",
    });
    setShowExplanation(prevAnswers.subAnswers?.[3] === "No");
    setExplanationText(prevAnswers.explanation || "");
  }, [prevAnswers, questionId]);
  
  const handleOptionChange = (subQuestionId: number) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;

    if (subQuestionId === 3) {
      if (value === "No") {
        setShowExplanation(true);
      } else {
        setShowExplanation(false);
        setExplanationText("");
      }
    }
    setSelectedAnswers(prev => ({
      ...prev,
      [subQuestionId]: value,
    }));
    onAnswer(questionId, posA, subQuestionId, value, explanationText);
  };

  const handleExplanationChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const explanation = event.target.value;
    setExplanationText(explanation);
    onAnswer(questionId, posA, 3, "No", explanation);
  };

  function formatText(text: string | null | undefined): JSX.Element {
    if (typeof text !== "string") {
      return <></>;
    }
    
    const parts = text.split(/(\*.*?\*)/);  // Split by asterisks
    return (
      <>
        {parts.map((part, index) =>
          part.startsWith("*") && part.endsWith("*") ? (
            <b key={index}>{part.slice(1, -1)}</b>  // Remove asterisks and bold the text
          ) : (
            part
          )
        )}
      </>
    );
  }

  return (
    <Card variant="outlined" sx={{ marginBottom: 2 }}>
      <CardContent>
        <Typography variant="h6" component="div" gutterBottom>
          Question {displayId}
        </Typography>

        {/* Display the conversation history in chat bubbles */}
        {history.length > 0 ? (
          <>
            {history.map((entry, index) => (
              <Box
                key={index}
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  mb: 1,
                  alignItems: index % 2 === 0 ? "flex-start" : "flex-end",
                }}
              >
                {entry.map((message, msgIdx) => (
                  message === "<COLLAPSED_INSIGHTS>" ? (
                    <>
                      <Box sx={{ textAlign: "center", mb: 2 }}>
                        <Typography variant="h6" sx={{ fontWeight: "bold", fontSize: "36px", color: "#666" }}>
                          ...
                        </Typography>
                      </Box>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          padding: "10px",
                          backgroundColor: "#DCDCDC",
                          borderRadius: "10px",
                          mb: 2,
                          border: "1px solid #D2D2D2",
                        }}
                      >
                        <InfoOutlinedIcon sx={{ mr: 1 }} />
                        <Typography variant="body2">
                          <i>The chatbot provides a basic update into the user&apos;s dietary intake over the last month.</i>
                        </Typography>
                      </Box>
                    </>
                  ) : (
                    <Typography
                      key={msgIdx}
                      variant="body1"
                      component="div"
                      sx={{
                        padding: "10px",
                        backgroundColor: index % 2 === 0 ? "#e0f7fa" : "#f1f8e9",
                        borderRadius: "10px",
                        maxWidth: "70%",
                        whiteSpace: "pre-wrap", // Preserve formatting
                        mb: 1,
                        textAlign: "left",
                      }}
                    >
                      {formatText(message)}
                    </Typography>
                  )
                ))}
              </Box>
            ))}
          </>
        ) : (
          <Box
            sx={{
              display: "inline-flex",
              alignItems: "flex-start",
              padding: "10px",
              backgroundColor: "#DCDCDC",
              borderRadius: "10px",
              mb: 2,
              border: "1px solid #D2D2D2",
            }}
          >
            <InfoOutlinedIcon sx={{ mr: 1 }} />
            <Typography variant="body2">
              <i>Here, you don&apos;t see a message from the user, as the chatbot is reaching out to the user first.</i>
            </Typography>
          </Box>
        )}

        {/* Display the responses side by side */}
        <Grid container spacing={2} sx={{ marginBottom: 2 }}>
          {shuffledOptions.map((option, idx) => (
            <Grid item xs={6} key={idx}>
              <Box
                sx={{
                  padding: "10px",
                  borderRadius: "10px",
                  border: "1px solid #ccc",
                  backgroundColor: "#f9f9f9",
                }}
              >
                <Typography variant="h6" align="center" sx={{ mb: 1 }}>
                  {option.label}
                </Typography>
                {option.text.map((message, msgIdx) => {
                // Map chart types to their respective image files
                const chartImages: { [key: string]: string } = {
                  "<FOOD_CHART>": "/images/food_chart.png",
                  "<LINE_CHART1>": "/images/line_chart1.png",
                  "<LINE_CHART2>": "/images/line_chart2.png",
                  "<LINE_CHART3>": "/images/line_chart3.png",
                  "<TREND_CHART>": "/images/trend_chart.png"
                };

                return chartImages[message] ? (
                  <Box
                    key={msgIdx}
                    sx={{
                      maxWidth: "100%",
                      mb: 1,
                    }}
                  >
                    <Image
                      src={chartImages[message]} // Load the appropriate image based on message
                      alt={`${message} Image`} // Provide alt text dynamically
                      width={2000}
                      height={2000}
                      sizes="100vw"
                      style={{
                        width: "100%",
                        height: "auto",
                        borderRadius: "10px",
                      }}
                    />
                  </Box>
                ) : (
                  <Box
                    key={msgIdx}
                    sx={{
                      padding: "10px",
                      backgroundColor: "#fff3e0",
                      borderRadius: "10px",
                      textAlign: "left",
                      mb: 1,
                    }}
                  >
                    <Typography
                      variant="body1"
                      component="div"
                      sx={{
                        whiteSpace: "pre-wrap", // Preserve formatting
                      }}
                    >
                      {formatText(message)}
                    </Typography>
                  </Box>
                );
              })}
              </Box>
            </Grid>
          ))}
        </Grid>

        {/* Question 1: Which response do you prefer? */}
        <Typography variant="body1" gutterBottom>
          <b>Which response do you prefer?</b>
        </Typography>
        <RadioGroup
          value={selectedAnswers[1] || ""}
          onChange={handleOptionChange(1)}
          sx={{ marginBottom: 2 }}
        >
          {shuffledOptions.map((option) => (
            <FormControlLabel
              key={option.type}
              value={option.type} // templated or rephrased
              control={<Radio />}
              label={option.label}
            />
          ))}
        </RadioGroup>

        {/* Question 2: Which response sounds more natural? */}
        <Typography variant="body1" gutterBottom>
          <b>Which response sounds more natural?</b>
        </Typography>
        <RadioGroup
          value={selectedAnswers[2] || ""}
          onChange={handleOptionChange(2)}
          sx={{ marginBottom: 2 }}
        >
          {shuffledOptions.map((option) => (
            <FormControlLabel
              key={option.type}
              value={option.type} // templated or rephrased
              control={<Radio />}
              label={option.label}
            />
          ))}
        </RadioGroup>

        {/* Question 3: Do both responses have the same meaning? */}
        <Typography variant="body1" gutterBottom>
          <b>Do both responses have the same meaning?</b>
        </Typography>
        <RadioGroup
          value={selectedAnswers[3] || ""}
          onChange={handleOptionChange(3)}
        >
          {["Yes", "No"].map((option) => (
            <FormControlLabel
              key={option}
              value={option}
              control={<Radio />}
              label={option}
            />
          ))}
        </RadioGroup>

        {/* Conditionally render the explanation text box if "No" is selected */}
        {showExplanation && (
          <TextField
            label="Why not?"
            multiline
            fullWidth
            minRows={3}
            value={explanationText}
            onChange={handleExplanationChange}
            variant="outlined"
            sx={{ marginTop: 2 }}
          />
        )}
      </CardContent>
    </Card>
  );
};

export default QuestionCard;
