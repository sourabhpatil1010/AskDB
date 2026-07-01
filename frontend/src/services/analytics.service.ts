/**
 * analytics.service.ts
 *
 * Reusable statistics calculation service for AskDB.
 * Serves as the single source of truth for all dashboard and analytics metrics,
 * ensuring consistent calculations across all presentation layers.
 */

import type { SearchHistory } from "../types/history";

export interface QueryStatistics {
  totalQueries: number;
  successfulQueries: number;
  failedQueries: number;
  averageExecutionTime: number; // in milliseconds
  successRate: number; // percentage value from 0 to 100 (e.g., 100, 99.3, 0)
}

export class AnalyticsService {
  /**
   * Calculates comprehensive query statistics from a user's search history.
   * Ensures identical metrics across Dashboard and Analytics pages.
   */
  public static calculateStatistics(history: SearchHistory[]): QueryStatistics {
    if (!history || history.length === 0) {
      return {
        totalQueries: 0,
        successfulQueries: 0,
        failedQueries: 0,
        averageExecutionTime: 0,
        successRate: 0,
      };
    }

    const totalQueries = history.length;
    let successfulQueries = 0;
    let totalExecutionTimeMs = 0;
    let completedCount = 0;

    for (const entry of history) {
      if (entry.status === "SUCCESS") {
        successfulQueries++;
      }
      if (
        entry.execution_time_ms !== undefined &&
        entry.execution_time_ms !== null
      ) {
        totalExecutionTimeMs += entry.execution_time_ms;
        completedCount++;
      }
    }

    const failedQueries = totalQueries - successfulQueries;

    const averageExecutionTime =
      completedCount > 0
        ? Math.round(totalExecutionTimeMs / completedCount)
        : 0;

    // Success Rate Formula: (successful_queries / total_queries) * 100
    // If total_queries == 0, return 0 to avoid divide-by-zero errors.
    const rawSuccessRate =
      totalQueries > 0 ? (successfulQueries / totalQueries) * 100 : 0;
    // Round to at most 1 decimal place (e.g., 99.333333 -> 99.3, 100.0 -> 100)
    const successRate = Number(rawSuccessRate.toFixed(1));

    return {
      totalQueries,
      successfulQueries,
      failedQueries,
      averageExecutionTime,
      successRate,
    };
  }
}

export const analyticsService = new AnalyticsService();
export { AnalyticsService as StatisticsService };
