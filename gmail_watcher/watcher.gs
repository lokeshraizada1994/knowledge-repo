// ─── CONFIG ────────────────────────────────────────────────────────────────
var WEBHOOK_URL = "YOUR_RAILWAY_URL/webhook";   // fill in after Step 6 deploy
var WEBHOOK_SECRET = "YOUR_WEBHOOK_SECRET";      // same as .env WEBHOOK_SECRET
var LABEL_NAME = "knowledge-processed";
// ───────────────────────────────────────────────────────────────────────────

function watchInbox() {
  var label = getOrCreateLabel(LABEL_NAME);

  // Search for unread emails not yet processed
  var threads = GmailApp.search("is:unread -label:" + LABEL_NAME, 0, 10);

  threads.forEach(function(thread) {
    var messages = thread.getMessages();
    var message = messages[messages.length - 1]; // latest message in thread

    var subject = message.getSubject();
    var body = message.getPlainBody();
    var attachments = [];

    // Handle attachments (PDFs, audio)
    message.getAttachments().forEach(function(att) {
      attachments.push({
        filename: att.getName(),
        mimeType: att.getContentType(),
        data: Utilities.base64Encode(att.getBytes())
      });
    });

    var payload = {
      subject: subject,
      body: body,
      attachments: attachments,
      from: message.getFrom(),
      date: message.getDate().toISOString()
    };

    try {
      var response = UrlFetchApp.fetch(WEBHOOK_URL, {
        method: "post",
        contentType: "application/json",
        headers: { "X-Webhook-Secret": WEBHOOK_SECRET },
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      });

      var code = response.getResponseCode();
      Logger.log("Sent: " + subject + " → HTTP " + code);

      if (code === 200) {
        // Mark as processed so we don't reprocess
        thread.addLabel(label);
        thread.markRead();
      }
    } catch(e) {
      Logger.log("Error sending " + subject + ": " + e.toString());
    }
  });
}

function getOrCreateLabel(name) {
  var label = GmailApp.getUserLabelByName(name);
  if (!label) {
    label = GmailApp.createLabel(name);
  }
  return label;
}

// Run this once manually to set up the 5-minute trigger
function createTrigger() {
  // Remove existing triggers first
  ScriptApp.getProjectTriggers().forEach(function(t) {
    ScriptApp.deleteTrigger(t);
  });

  ScriptApp.newTrigger("watchInbox")
    .timeBased()
    .everyMinutes(5)
    .create();

  Logger.log("Trigger created — watchInbox will run every 5 minutes");
}
