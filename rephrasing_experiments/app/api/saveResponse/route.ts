import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const filePath = path.join(process.cwd(), 'app/data/responses.json');

export async function POST(request: NextRequest) {
  try {
    const data = await request.json();
    const { participantID, answers } = data;

    // Read existing responses
    let responses = [];
    if (fs.existsSync(filePath)) {
      const fileData = fs.readFileSync(filePath, 'utf-8');
      responses = JSON.parse(fileData);
    }

    // Save the answers with participantID as the key
    responses[participantID] = answers;

    // Write updated responses back to file
    fs.writeFileSync(filePath, JSON.stringify(responses, null, 2));

    return NextResponse.json({ message: 'Response saved successfully' });
  } catch (error) {
    console.error('Error saving response:', error);
    return NextResponse.json({ message: 'Failed to save response' }, { status: 500 });
  }
}