// ─── CONFIG ────────────────────────────────────────────────────────────────
var WEBHOOK_URL = "https://knowledge-repo-b4rj.onrender.com/webhook";
var WEBHOOK_SECRET = "YOUR_WEBHOOK_SECRET";  // keep your actual secret here
var LABEL_NAME = "knowledge-processed";
// ───────────────────────────────────────────────────────────────────────────

function watchInbox() {
  var label = getOrCreateLabel(LABEL_NAME);

  // Search ALL emails (read and unread) not yet labelled as processed
  var threads = GmailApp.search("-label:" + LABEL_NAME, 0, 20);

  threads.forEach(function(thread) {
    // Always label the thread first — prevents reprocessing even if webhook fails
    thread.addLabel(label);
    thread.markRead();

    var messages = thread.getMessages();
    var message = messages[messages.length - 1];

    var subject = message.getSubject();
    var body = message.getPlainBody();
    var attachments = [];

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

// Run this once to label all existing emails so they don't get reprocessed
function labelAllExisting() {
  var label = getOrCreateLabel(LABEL_NAME);
  var threads = GmailApp.search("-label:" + LABEL_NAME, 0, 500);
  threads.forEach(function(thread) {
    thread.addLabel(label);
    thread.markRead();
  });
  Logger.log("Labelled " + threads.length + " existing threads as processed");
}

function createTrigger() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger("watchInbox")
    .timeBased()
    .everyMinutes(1)
    .create();
  Logger.log("Trigger created — watchInbox will run every 1 minute");
}
