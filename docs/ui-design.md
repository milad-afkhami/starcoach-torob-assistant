# Current UI direction

The current direction is [conversation-first correction](conversation-design.md). One chronological Persian conversation is the principal screen. Assistant replies introduce bounded source-backed components, then continue with a clear next step. Products, comparisons, seller cards, actual-coordinate maps, revision deltas and explicit proposals live inside the conversation. A bottom composer is the primary action; manual search and filters are secondary tools.

The former split search/results workspace with a permanent purchase sidebar is retired. Do not recreate it or use earlier screenshot evidence as acceptance for this revision. The conversation QA plan in `insured-vibe-coding/test-plans/conversation.md` owns the new rendered acceptance; earlier QA records remain historical regression evidence.

The domain boundary remains unchanged: exact decimal money, one exact product per mission, explicit condition changes and observation confirmation, source price dates, declared hours, unknown stock, synthetic contacts, source coordinate markers, deterministic fallback, bounded model turns and revision/ownership guards. Model output refers to allowlisted retrieved IDs and is rendered with fixed React components; it cannot create arbitrary HTML or JavaScript.

Conversation messages persist while this page remains open. Reload restores the owned saved mission from the API and explicitly says that earlier messages were not restored. “New conversation” cancels the owned pending turn, removes conversation/discovery/proposal/plan references from the UI and browser's last-mission pointer, and does not delete server audit records. History does not silently become a new model context.
