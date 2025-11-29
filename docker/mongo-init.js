db = db.getSiblingDB('studybuddy');

db.createCollection('documents', { capped: false });
db.createCollection('flashcards', { capped: false });
db.createCollection('assessments', { capped: false });
db.createCollection('tasks', { capped: false });

db.tasks.createIndex({ "createdAt": 1 }, { expireAfterSeconds: 86400 }); // Tasks expire after 24 hours

print("MongoDB initialized and collections created.");
