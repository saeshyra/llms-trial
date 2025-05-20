import React from "react";
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography } from "@mui/material";

interface InstructionsDialogProps {
  open: boolean;
  onClose: () => void;
}

const InstructionsDialog: React.FC<InstructionsDialogProps> = ({ open, onClose }) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="md"
    >
      <DialogTitle>Survey Instructions</DialogTitle>
      <DialogContent>
        <Typography variant="body1" component="div" paragraph>
        In this experiment, you will see different messages coming from a diet-coaching chatbot. The chatbot&apos;s goal is to provide insights into what a user ate. Your task is to assess and compare the given responses.
        </Typography>
        <Typography variant="body1" component="div" paragraph>
          <b>Conversation history:</b> If it&apos;s relevant to the text messages you are comparing, you will see the conversation history leading up to the messages. This can include the user&apos;s request for their calorie or nutritional intake, or other dietary insights. Otherwise, you will be given any other necessary context. 
        </Typography>
        <Typography variant="body1" component="div">
          <b>Responses to compare:</b> You will see 2 different responses from the chatbot, both addressing the same user message at the beginning (if any). For each pair of responses, you will be asked 3 questions:
        </Typography>
        <Typography variant="body1" component="li">
          <u>Which response do you prefer?</u> Consider which message you would prefer to receive from the chatbot.
        </Typography>
        <Typography variant="body1" component="li">
          <u>Which response sounds more natural?</u> Consider which message sounds more natural given the conversation history (if any).
        </Typography>
        <Typography variant="body1" component="li" paragraph>
          <u>Do both responses have the same meaning?</u> Assess whether both responses convey the same insights and information. If you think the meanings differ, please explain why (optional).
        </Typography>
        <Typography variant="body1" component="div">
          At any given point <b>before submission</b>, you can go back to previous questions to change your answers.
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="primary">
          Understood!
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default InstructionsDialog;
