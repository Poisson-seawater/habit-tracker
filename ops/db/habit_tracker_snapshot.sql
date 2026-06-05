-- Habit Tracker SQLite snapshot
-- Generated at 2026-06-05T17:08:23
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE daily_scores (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	status VARCHAR, 
	template_used VARCHAR NOT NULL, 
	actual_stats JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
INSERT INTO "daily_scores" VALUES(3,3,'2026-06-04','Failed','weekend','{"force": 3, "endurance": 0, "mobilite": 0, "discipline": 6, "creativite": 0, "connaissance": 6, "sociabilite": 0, "sante_mentale": 0, "finance": 0, "organisation": 0, "spiritualite": 0, "repos": 0}');
INSERT INTO "daily_scores" VALUES(4,4,'2026-06-04','Failed','week','{"force": 0, "endurance": 0, "mobilite": 0, "discipline": 0, "creativite": 0, "connaissance": 0, "sociabilite": 0, "sante_mentale": 0, "finance": 0, "organisation": 0, "spiritualite": 0, "repos": 0}');
INSERT INTO "daily_scores" VALUES(6,3,'2026-06-05','Failed','week','{"force": 0, "endurance": 0, "mobilite": 0, "discipline": 0, "creativite": 0, "connaissance": 0, "sociabilite": 0, "sante_mentale": 0, "finance": 0, "organisation": 0, "spiritualite": 0, "repos": 0}');
CREATE TABLE goal_substep_links (
	id INTEGER NOT NULL, 
	goal_id INTEGER NOT NULL, 
	substep_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(goal_id) REFERENCES goals (id) ON DELETE CASCADE, 
	FOREIGN KEY(substep_id) REFERENCES substeps (id) ON DELETE CASCADE
);
INSERT INTO "goal_substep_links" VALUES(1,1,1);
INSERT INTO "goal_substep_links" VALUES(2,1,2);
INSERT INTO "goal_substep_links" VALUES(3,1,3);
INSERT INTO "goal_substep_links" VALUES(4,2,4);
INSERT INTO "goal_substep_links" VALUES(5,2,5);
INSERT INTO "goal_substep_links" VALUES(6,2,6);
INSERT INTO "goal_substep_links" VALUES(7,2,7);
INSERT INTO "goal_substep_links" VALUES(8,3,8);
INSERT INTO "goal_substep_links" VALUES(9,3,9);
INSERT INTO "goal_substep_links" VALUES(10,3,10);
CREATE TABLE goals (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	description TEXT, 
	completed BOOLEAN, 
	completed_at DATETIME, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
INSERT INTO "goals" VALUES(1,3,'Devenir Millionnaire','Atteindre la liberté financière absolue',0,NULL,'2026-06-04 02:48:03.828650');
INSERT INTO "goals" VALUES(2,3,'Faire le tour du monde','Explorer toutes les merveilles de la Terre',0,NULL,'2026-06-04 02:48:03.828654');
INSERT INTO "goals" VALUES(3,3,'Avoir des enfants','Fonder une famille aimante et stable',0,NULL,'2026-06-04 02:48:03.828655');
INSERT INTO "goals" VALUES(4,3,'manger du poulet','miam miam miam',0,NULL,'2026-06-04 19:36:19.952102');
CREATE TABLE habit_logs (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	habit_id INTEGER NOT NULL, 
	timestamp DATETIME, 
	log_type VARCHAR NOT NULL, 
	amount INTEGER, 
	unit VARCHAR, 
	reason VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(habit_id) REFERENCES habits (id) ON DELETE CASCADE
);
INSERT INTO "habit_logs" VALUES(1,3,7,'2026-06-04 15:44:02.436613','log',30,'min',NULL);
INSERT INTO "habit_logs" VALUES(2,3,6,'2026-06-04 19:53:54.159975','done',NULL,NULL,NULL);
INSERT INTO "habit_logs" VALUES(3,3,7,'2026-06-04 19:54:20.956492','log',30,'min',NULL);
INSERT INTO "habit_logs" VALUES(4,3,8,'2026-06-04 19:55:25.289213','skip',NULL,NULL,'fiu');
CREATE TABLE habits (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	description TEXT, 
	type VARCHAR NOT NULL, 
	frequency VARCHAR, 
	scheduled_days VARCHAR, 
	reminder_time VARCHAR, 
	is_private BOOLEAN, 
	is_reportable BOOLEAN, 
	is_mandatory BOOLEAN, 
	point_rewards JSON NOT NULL, 
	daily_cap INTEGER, 
	unit VARCHAR, 
	is_active BOOLEAN, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_user_habit_name UNIQUE (user_id, name), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
INSERT INTO "habits" VALUES(2,3,'lecture','Lecture active de livres techniques, de fiction ou de philosophie.','quantitative','daily','0,1,2,3,4,5,6','21:00',0,1,0,'{"creativite": 5, "discipline": 2, "connaissance": 3}',8,'min',1);
INSERT INTO "habits" VALUES(4,3,'nage','Session piscine ou natation cardio.','quantitative','weekly','2,4','12:00',0,1,0,'{"force": 8, "endurance": 5, "mobilite": 3}',15,'km',1);
INSERT INTO "habits" VALUES(5,3,'meditation','Méditation pleine conscience (gardé privé).','binary','daily','0,1,2,3,4,5,6','07:00',1,0,0,'{"sante_mentale": 3, "repos": 2}',NULL,NULL,1);
INSERT INTO "habits" VALUES(6,3,'pompes',NULL,'binary','daily','0,1,2,3,4,5,6',NULL,0,1,0,'{"force": 3, "discipline": 2}',NULL,NULL,1);
INSERT INTO "habits" VALUES(7,3,'lecture_panda',NULL,'quantitative','daily','0,1,2,3,4,5,6',NULL,0,1,0,'{"connaissance": 3, "discipline": 2}',8,'min',1);
INSERT INTO "habits" VALUES(8,3,'routine_matin','pisser et doucher','binary','daily','0,1,2,3,4,5,6',NULL,0,1,0,'{"discipline": 5}',NULL,NULL,1);
INSERT INTO "habits" VALUES(9,3,'Ukulele',NULL,'binary','daily','0,1,2,3,4,5,6',NULL,0,1,0,'{"discipline": 1}',NULL,NULL,1);
INSERT INTO "habits" VALUES(10,3,'Course',NULL,'quantitative','daily','0,1,2,3,4,5,6',NULL,0,1,0,'{"discipline": 1}',NULL,'km',1);
INSERT INTO "habits" VALUES(11,3,'Manger du poisson',NULL,'binary','daily','0,1,2,3,4,5,6',NULL,0,1,0,'{"discipline": 1}',NULL,NULL,1);
CREATE TABLE notodos (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	created_at DATETIME, 
	failed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
INSERT INTO "notodos" VALUES(11,3,'Scroller sur les réseaux sociaux le matin','2026-06-04 19:16:14.527181',NULL);
INSERT INTO "notodos" VALUES(12,3,'Repousser le réveil (Snooze)','2026-06-04 19:16:14.527182','2026-06-04 19:55:48.469104');
INSERT INTO "notodos" VALUES(13,3,'Manger de la junk food en semaine','2026-06-04 19:16:14.527183',NULL);
INSERT INTO "notodos" VALUES(14,3,'Se plaindre sans chercher de solution','2026-06-04 19:16:14.527184',NULL);
INSERT INTO "notodos" VALUES(15,3,'Boire de l''alcool en semaine','2026-06-04 19:16:14.527184',NULL);
INSERT INTO "notodos" VALUES(16,3,'Regarder la TV avant de dormir','2026-06-04 19:16:14.527185',NULL);
INSERT INTO "notodos" VALUES(17,3,'pisser sur les plantes','2026-06-04 19:46:46.728903','2026-06-04 19:48:24.523233');
INSERT INTO "notodos" VALUES(18,3,'Scroller sur TikTok','2026-06-04 19:56:35.920461',NULL);
CREATE TABLE perfect_day_templates (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	template_name VARCHAR NOT NULL, 
	thresholds_json JSON NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
INSERT INTO "perfect_day_templates" VALUES(1,3,'week','{"discipline": 8, "organisation": 3, "creativite": 3, "connaissance": 3}');
INSERT INTO "perfect_day_templates" VALUES(2,3,'weekend','{"repos": 8, "sociabilite": 4, "creativite": 3}');
INSERT INTO "perfect_day_templates" VALUES(3,3,'recup','{"repos": 5, "sante_mentale": 3}');
INSERT INTO "perfect_day_templates" VALUES(4,3,'malade','{"repos": 3}');
CREATE TABLE streaks (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	streak_type VARCHAR NOT NULL, 
	current_streak INTEGER, 
	max_streak INTEGER, 
	last_incremented DATE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
INSERT INTO "streaks" VALUES(1,3,'Perfect',0,0,NULL);
INSERT INTO "streaks" VALUES(2,3,'habit:7',1,1,'2026-06-04');
INSERT INTO "streaks" VALUES(3,3,'habit:6',1,1,'2026-06-04');
INSERT INTO "streaks" VALUES(4,3,'habit:8',0,0,'2026-06-04');
INSERT INTO "streaks" VALUES(5,3,'habit:10',0,0,NULL);
INSERT INTO "streaks" VALUES(6,3,'habit:9',0,0,NULL);
CREATE TABLE substeps (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	gold_reward INTEGER, 
	completed BOOLEAN, 
	completed_at DATETIME, 
	description TEXT, 
	stats_json JSON, 
	execution_order INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
INSERT INTO "substeps" VALUES(1,3,'Avoir 500k en actif',500,0,NULL,'Accumuler 500k d''actifs nets','["finance"]',1,'2026-06-04 02:48:03.832628');
INSERT INTO "substeps" VALUES(2,3,'Acheter un immeuble locatif',300,0,NULL,'Trouver et acquérir un premier bien de rendement','["finance", "organisation"]',1,'2026-06-04 02:48:03.832629');
INSERT INTO "substeps" VALUES(3,3,'Trouver un bon avocat',100,0,NULL,'Réseauter pour s''entourer d''un expert juridique','["discipline", "organisation"]',1,'2026-06-04 02:48:03.832629');
INSERT INTO "substeps" VALUES(4,3,'Avoir de l''argent',150,0,NULL,'Constituer une épargne de voyage','["finance"]',1,'2026-06-04 02:48:03.832630');
INSERT INTO "substeps" VALUES(5,3,'Avoir un passeport',50,0,NULL,'Faire les démarches à la mairie','["organisation"]',1,'2026-06-04 02:48:03.832630');
INSERT INTO "substeps" VALUES(6,3,'Créer une feuille de budget',75,0,NULL,'Suivre ses dépenses mensuelles','["finance", "organisation"]',1,'2026-06-04 02:48:03.832630');
INSERT INTO "substeps" VALUES(7,3,'Achat assurance vie',100,0,NULL,'Sécuriser un contrat d''assurance vie','["finance"]',1,'2026-06-04 02:48:03.832630');
INSERT INTO "substeps" VALUES(8,3,'Avoir une entrée d''argent stable',200,0,NULL,'Garantir un flux financier mensuel régulier','["finance"]',1,'2026-06-04 02:48:03.832630');
INSERT INTO "substeps" VALUES(9,3,'Trouver une femme',150,0,NULL,'Rencontrer sa partenaire de vie idéale','["sociabilite"]',1,'2026-06-04 02:48:03.832630');
INSERT INTO "substeps" VALUES(10,3,'La marier',250,0,NULL,'Célébrer notre union','["sociabilite", "spiritualite"]',1,'2026-06-04 02:48:03.832631');
CREATE TABLE todos (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	stat_reward_1 VARCHAR, 
	points_reward_1 INTEGER, 
	stat_reward_2 VARCHAR, 
	points_reward_2 INTEGER, 
	xp_reward INTEGER, 
	is_completed BOOLEAN, 
	created_at DATETIME, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
INSERT INTO "todos" VALUES(1,3,'⚔️ Dompter le Dragon de Fer (Séance Jambes)','force',16,NULL,0,20,0,'2026-06-04 02:48:03.833918',NULL);
INSERT INTO "todos" VALUES(2,3,'📚 Décoder les Runes (Lire 20 pages de doc)','connaissance',3,NULL,0,10,0,'2026-06-04 02:48:03.833918',NULL);
INSERT INTO "todos" VALUES(4,3,'se brosser les dents',NULL,5,NULL,0,20,0,'2026-06-04 19:52:44.720544',NULL);
INSERT INTO "todos" VALUES(5,3,'Faire les courses',NULL,0,NULL,0,10,0,'2026-06-04 19:56:29.654341',NULL);
CREATE TABLE users (
	id INTEGER NOT NULL, 
	username VARCHAR NOT NULL, 
	chat_id VARCHAR, 
	xp INTEGER, 
	level INTEGER, 
	gold INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (username)
);
INSERT INTO "users" VALUES(3,'Gabriel','6659224082',0,1,0,NULL);
INSERT INTO "users" VALUES(4,'benjamin_deriv','5915574324',0,1,0,'2026-06-04 17:36:05.658933');
CREATE UNIQUE INDEX ix_users_chat_id ON users (chat_id);
CREATE INDEX ix_users_id ON users (id);
CREATE INDEX ix_habits_name ON habits (name);
CREATE INDEX ix_habits_id ON habits (id);
CREATE INDEX ix_perfect_day_templates_id ON perfect_day_templates (id);
CREATE INDEX ix_daily_scores_id ON daily_scores (id);
CREATE INDEX ix_daily_scores_date ON daily_scores (date);
CREATE INDEX ix_streaks_id ON streaks (id);
CREATE INDEX ix_todos_id ON todos (id);
CREATE INDEX ix_goals_id ON goals (id);
CREATE INDEX ix_substeps_id ON substeps (id);
CREATE INDEX ix_habit_logs_id ON habit_logs (id);
CREATE INDEX ix_goal_substep_links_id ON goal_substep_links (id);
CREATE INDEX ix_notodos_id ON notodos (id);
COMMIT;
PRAGMA foreign_keys=ON;
