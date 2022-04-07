DROP TABLE IF EXISTS `unvalidated_email_log`;
CREATE TABLE `unvalidated_email_log` (
  `unvalidated_email_id` int NOT NULL AUTO_INCREMENT,
  `aws_sns_message_id` varchar(100) DEFAULT NULL,
  `source_address` varchar(100) DEFAULT NULL,
  `destination_address` varchar(100) DEFAULT NULL,
  `subject` varchar(100) DEFAULT NULL,
  `source_ip` varchar(100) DEFAULT NULL,
  `source_arn` varchar(100) DEFAULT NULL,
  `timestamp` timestamp NULL DEFAULT NULL,
  `status` varchar(100) DEFAULT NULL,
  `diagnostic_code` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`unvalidated_email_id`)
);

--
-- Table structure for table `user`
--
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `user_id` int NOT NULL,
  `email_address` varchar(45) DEFAULT NULL,
  `validated` int DEFAULT NULL,
  PRIMARY KEY (`user_id`)
);

--
-- Table structure for table `user_email_log`
--
DROP TABLE IF EXISTS `user_email_log`;
CREATE TABLE `user_email_log` (
  `user_email_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `aws_sns_message_id` varchar(100) DEFAULT NULL,
  `source_address` varchar(100) DEFAULT NULL,
  `subject` varchar(100) DEFAULT NULL,
  `source_ip` varchar(100) DEFAULT NULL,
  `source_arn` varchar(100) DEFAULT NULL,
  `timestamp` timestamp NULL DEFAULT NULL,
  `status` varchar(100) DEFAULT NULL,
  `diagnostic_code` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`user_email_id`)
);
