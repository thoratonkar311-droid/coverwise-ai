import { ApiError } from "@/types";

export class CoverWiseApiError extends Error implements ApiError {
  public statusCode: number;
  public code?: string;
  public details?: string | Record<string, unknown>;
  public timestamp: string;

  constructor(
    statusCode: number,
    message: string,
    options?: {
      code?: string;
      details?: string | Record<string, unknown>;
    }
  ) {
    super(message);
    this.name = "CoverWiseApiError";
    this.statusCode = statusCode;
    this.code = options?.code;
    this.details = options?.details;
    this.timestamp = new Date().toISOString();

    // Prevent leaking internal stack trace in production environments
    if (process.env.NODE_ENV === "production") {
      this.stack = undefined;
    }
  }
}

/**
 * Maps HTTP status codes and common network failures to user-friendly messages.
 * Does not expose internal server traces or database messages to end users.
 */
export function parseApiError(error: unknown): ApiError {
  if (error instanceof CoverWiseApiError) {
    return {
      statusCode: error.statusCode,
      message: error.message,
      code: error.code,
      details: error.details,
      timestamp: error.timestamp,
    };
  }

  // Handle AbortController timeout
  if (error instanceof DOMException && error.name === "AbortError") {
    return {
      statusCode: 408,
      code: "REQUEST_TIMEOUT",
      message: "The request timed out. The policy analysis engine took longer than expected to respond.",
      details: "Please check your network connection or try analyzing a smaller document.",
      timestamp: new Date().toISOString(),
    };
  }

  // Handle standard TypeError from failed network fetch
  if (error instanceof TypeError && error.message.includes("fetch")) {
    return {
      statusCode: 0,
      code: "NETWORK_ERROR",
      message: "Unable to connect to CoverWise AI servers. Please verify your internet connection.",
      details: "The network request failed before reaching the server.",
      timestamp: new Date().toISOString(),
    };
  }

  // Generic fallback without exposing internal stack trace
  return {
    statusCode: 500,
    code: "UNEXPECTED_ERROR",
    message: "An unexpected error occurred while processing your request. Please try again.",
    timestamp: new Date().toISOString(),
  };
}

/**
 * Creates standardized user-friendly error objects based on HTTP status code.
 */
export function createHttpError(
  statusCode: number,
  customMessage?: string,
  details?: string | Record<string, unknown>
): CoverWiseApiError {
  let message = customMessage;
  let code = `HTTP_${statusCode}`;

  switch (statusCode) {
    case 400:
      message =
        message ||
        "The request could not be processed due to invalid parameters or formatting.";
      code = "BAD_REQUEST";
      break;
    case 401:
      message =
        message ||
        "Authentication required. Please sign in to access your policy intelligence.";
      code = "UNAUTHORIZED";
      break;
    case 403:
      message =
        message ||
        "Access denied. You do not have permissions to view this policy document.";
      code = "FORBIDDEN";
      break;
    case 404:
      message =
        message ||
        "The requested policy schedule or treatment analysis was not found.";
      code = "NOT_FOUND";
      break;
    case 422:
      message =
        message ||
        "Validation failed. The policy document structure could not be parsed into recognized clauses.";
      code = "UNPROCESSABLE_ENTITY";
      break;
    case 500:
      message =
        message ||
        "An internal server error occurred within the intelligence analysis pipeline. Our engineers have been alerted.";
      code = "INTERNAL_SERVER_ERROR";
      break;
    default:
      message = message || "An unexpected error occurred. Please try again.";
      break;
  }

  return new CoverWiseApiError(statusCode, message, { code, details });
}
