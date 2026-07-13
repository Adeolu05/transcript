export interface TranscriptSegment {
    start: number;
    text: string;
}

export interface TranscriptResult {
    videoId: string;
    title: string;
    segments: TranscriptSegment[];
    summary?: string;
}

export enum ProcessingStatus {
    IDLE = 'IDLE',
    ANALYZING = 'ANALYZING',
    EXTRACTING = 'EXTRACTING',
    FORMATTING = 'FORMATTING',
    COMPLETE = 'COMPLETE',
    ERROR = 'ERROR',
}

export type FileFormat = 'txt' | 'docx' | 'pdf';
