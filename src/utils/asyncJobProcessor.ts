/**
 * Utility for processing async multi-agent jobs with polling
 * Handles Cloudflare timeout issues by using async job pattern
 */

export interface JobSubmitResponse {
  job_id: string;
  status: string;
  message: string;
  created_at: string;
  estimated_completion_seconds?: number;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  message?: string;
  created_at: string;
  updated_at: string;
  estimated_remaining_seconds?: number;
}

export interface JobResultResponse {
  job_id: string;
  status: 'completed' | 'failed';
  result?: any;
  error?: string;
  created_at: string;
  completed_at?: string;
}

export interface AsyncJobOptions {
  apiUrl: string;
  token: string;
  onProgress?: (status: JobStatusResponse) => void;
  pollInterval?: number; // milliseconds, default 2000
  maxPollAttempts?: number; // default 150 (5 minutes at 2s intervals)
  timeout?: number; // milliseconds, default 300000 (5 minutes)
}

/**
 * Submit a multi-agent job and poll for results
 */
export async function processAsyncJob(
  request: any,
  options: AsyncJobOptions
): Promise<any> {
  const {
    apiUrl,
    token,
    onProgress,
    pollInterval = 2000,
    maxPollAttempts = 150,
    timeout = 300000, // 5 minutes
  } = options;

  // Step 1: Submit job
  const submitResponse = await fetch(`${apiUrl}/api/multi-agent/submit`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ request }),
  });

  if (!submitResponse.ok) {
    const errorText = await submitResponse.text();
    let errorMessage = `Failed to submit job: ${submitResponse.status}`;
    try {
      const errorData = JSON.parse(errorText);
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      errorMessage = errorText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  const submitData: JobSubmitResponse = await submitResponse.json();
  const jobId = submitData.job_id;

  console.log('Job submitted:', { jobId, estimatedSeconds: submitData.estimated_completion_seconds });

  // Step 2: Poll for status
  const startTime = Date.now();
  let attempts = 0;

  while (attempts < maxPollAttempts) {
    // Check timeout
    if (Date.now() - startTime > timeout) {
      throw new Error('Job processing timeout exceeded');
    }

    // Wait before polling (except first attempt)
    if (attempts > 0) {
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    attempts++;

    try {
      const statusResponse = await fetch(`${apiUrl}/api/multi-agent/jobs/${jobId}/status`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        credentials: 'include',
      });

      if (!statusResponse.ok) {
        if (statusResponse.status === 404) {
          throw new Error('Job not found');
        }
        throw new Error(`Failed to get job status: ${statusResponse.status}`);
      }

      const status: JobStatusResponse = await statusResponse.json();

      // Call progress callback
      if (onProgress) {
        onProgress(status);
      }

      console.log('Job status:', {
        jobId,
        status: status.status,
        progress: status.progress,
        message: status.message,
        attempt: attempts,
      });

      // Check if completed or failed
      if (status.status === 'completed') {
        // Get result
        const resultResponse = await fetch(`${apiUrl}/api/multi-agent/jobs/${jobId}/result`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          credentials: 'include',
        });

        if (!resultResponse.ok) {
          throw new Error(`Failed to get job result: ${resultResponse.status}`);
        }

        const result: JobResultResponse = await resultResponse.json();

        if (result.status === 'failed') {
          throw new Error(result.error || 'Job processing failed');
        }

        if (!result.result) {
          throw new Error('Job completed but no result available');
        }

        console.log('Job completed successfully:', { jobId, result: result.result });
        return result.result;
      }

      if (status.status === 'failed') {
        // Try to get error details
        try {
          const resultResponse = await fetch(`${apiUrl}/api/multi-agent/jobs/${jobId}/result`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
            credentials: 'include',
          });

          if (resultResponse.ok) {
            const result: JobResultResponse = await resultResponse.json();
            throw new Error(result.error || 'Job processing failed');
          }
        } catch (e) {
          if (e instanceof Error) {
            throw e;
          }
        }
        throw new Error(status.message || 'Job processing failed');
      }

      // Continue polling if pending or processing
      if (status.status === 'pending' || status.status === 'processing') {
        continue;
      }

    } catch (error) {
      // If it's a known error, throw it
      if (error instanceof Error && (
        error.message.includes('timeout') ||
        error.message.includes('not found') ||
        error.message.includes('failed')
      )) {
        throw error;
      }

      // For network errors, log and continue polling
      console.warn('Error polling job status:', error);
      
      // If we've tried many times, give up
      if (attempts >= maxPollAttempts) {
        throw new Error('Failed to get job status after multiple attempts');
      }
    }
  }

  throw new Error('Job processing timeout: maximum polling attempts exceeded');
}

