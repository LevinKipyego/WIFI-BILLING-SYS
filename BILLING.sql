-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Dec 21, 2025 at 09:12 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `BILLING`
--

-- --------------------------------------------------------

--
-- Table structure for table `hotspot_users`
--

CREATE TABLE `hotspot_users` (
  `id` int(11) NOT NULL,
  `plan_id` int(11) NOT NULL,
  `vendor_id` char(36) NOT NULL,
  `transaction_uuid` varchar(64) DEFAULT NULL,
  `mac` varchar(64) DEFAULT NULL,
  `username` varchar(128) DEFAULT NULL,
  `mikrotik_profile` varchar(128) DEFAULT NULL,
  `expires_at` datetime DEFAULT NULL,
  `active` tinyint(1) DEFAULT 1,
  `created_at` datetime DEFAULT current_timestamp(),
  `client_ip` varchar(100) DEFAULT NULL,
  `link_login` varchar(200) NOT NULL DEFAULT 'http:/levine.net/login',
  `code_6char` varchar(50) NOT NULL DEFAULT 'Hello@2020',
  `session_status` enum('active','expired') NOT NULL DEFAULT 'active',
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `mikrotik_id` int(11) DEFAULT NULL,
  `mikrotik_identity_name` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `hotspot_users`
--

INSERT INTO `hotspot_users` (`id`, `plan_id`, `vendor_id`, `transaction_uuid`, `mac`, `username`, `mikrotik_profile`, `expires_at`, `active`, `created_at`, `client_ip`, `link_login`, `code_6char`, `session_status`, `updated_at`, `mikrotik_id`, `mikrotik_identity_name`) VALUES
(57, 1, 'xcvt', '53b9041b-37bd-4fd9-94a2-fa6202a71a5a', 'E2:04:40:FC:F3:3C', '254712083124', '1hr', '2025-12-12 01:31:24', 1, '2025-12-10 09:50:48', '10.0.0.249', 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', '37UZ5Q', 'expired', '2025-12-17 22:42:18', NULL, NULL),
(58, 1, 'xcvt', '90bcac29-1f75-4aa2-92a6-7ad2d65eaf16', 'E2:04:40:FC:F3:3C', '254791241206', '1hr', '2025-12-20 00:33:51', 1, '2025-12-15 22:59:24', '10.0.0.249', 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'ueWM3Z', 'expired', '2025-12-20 00:34:47', 1, 'MikroTik');

-- --------------------------------------------------------

--
-- Table structure for table `mikrotik_devices`
--

CREATE TABLE `mikrotik_devices` (
  `id` int(11) NOT NULL,
  `vendor_id` char(36) DEFAULT NULL,
  `identity_name` varchar(100) DEFAULT NULL,
  `serial_number` varchar(50) DEFAULT NULL,
  `api_ip` varchar(45) DEFAULT NULL,
  `enabled` tinyint(4) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `mikrotik_devices`
--

INSERT INTO `mikrotik_devices` (`id`, `vendor_id`, `identity_name`, `serial_number`, `api_ip`, `enabled`, `created_at`) VALUES
(1, 'xcvt', 'mikrotik', NULL, NULL, 1, '2025-12-19 10:00:37');

-- --------------------------------------------------------

--
-- Table structure for table `plans`
--

CREATE TABLE `plans` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `price` int(11) NOT NULL,
  `duration_min` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `plans`
--

INSERT INTO `plans` (`id`, `name`, `price`, `duration_min`) VALUES
(1, '1 hour plan', 1, 1);

-- --------------------------------------------------------

--
-- Table structure for table `radius_sessions`
--

CREATE TABLE `radius_sessions` (
  `acct_session_id` varchar(100) NOT NULL,
  `mikrotik_id` int(11) DEFAULT NULL,
  `username` varchar(100) DEFAULT NULL,
  `input_octets` bigint(20) DEFAULT NULL,
  `output_octets` bigint(20) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `stop_time` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `router_revenue_rules`
--

CREATE TABLE `router_revenue_rules` (
  `mikrotik_id` int(11) NOT NULL,
  `vendor_share` decimal(5,2) DEFAULT NULL,
  `platform_share` decimal(5,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `transactions`
--

CREATE TABLE `transactions` (
  `id` int(11) NOT NULL,
  `transaction_uuid` varchar(50) NOT NULL,
  `client_phone` varchar(20) NOT NULL,
  `plan_id` int(11) NOT NULL,
  `amount` int(11) NOT NULL,
  `status` varchar(20) DEFAULT 'pending',
  `mpesa_receipt` varchar(50) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `transactions`
--

INSERT INTO `transactions` (`id`, `transaction_uuid`, `client_phone`, `plan_id`, `amount`, `status`, `mpesa_receipt`, `created_at`) VALUES
(78, 'ff3d701f-8bd7-432b-a9da-f102ec04186f', '254712083124', 1, 1, 'pending', NULL, '2025-11-28 22:41:15'),
(79, '4626f4f3-2126-419a-ac9b-5c308a95c6fb', '254712083124', 1, 1, 'pending', NULL, '2025-11-28 22:44:37'),
(80, '5786cc2b-79af-4e70-a907-8ce1a5fedaaf', '254712083124', 1, 1, 'pending', NULL, '2025-11-28 23:13:27'),
(81, '16c1c0a8-9fd8-458e-b26c-fea76fa24524', '254712083124', 1, 1, 'pending', NULL, '2025-12-01 02:10:40'),
(82, '957e2e04-a8cc-467a-8bb4-87df21f9a265', '254712083124', 1, 1, 'pending', NULL, '2025-12-01 02:14:47');

-- --------------------------------------------------------

--
-- Table structure for table `user_plans`
--

CREATE TABLE `user_plans` (
  `id` int(11) NOT NULL,
  `name` varchar(128) DEFAULT NULL,
  `price` decimal(10,2) DEFAULT NULL,
  `duration_minutes` int(11) DEFAULT NULL,
  `mikrotik_profile` varchar(128) DEFAULT NULL,
  `rate_limit` varchar(64) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `mikrotik_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `user_plans`
--

INSERT INTO `user_plans` (`id`, `name`, `price`, `duration_minutes`, `mikrotik_profile`, `rate_limit`, `created_at`, `mikrotik_id`) VALUES
(1, '1 Hour', 1.00, 60, '1hr', '1M/1M', '2025-11-28 20:49:41', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `user_sessions`
--

CREATE TABLE `user_sessions` (
  `id` bigint(20) NOT NULL,
  `radacctid` bigint(20) NOT NULL,
  `acctuniqueid` varchar(32) NOT NULL,
  `user_id` char(36) NOT NULL,
  `vendor_id` char(36) NOT NULL,
  `mikrotik_id` char(36) NOT NULL,
  `session_start` datetime NOT NULL,
  `session_end` datetime DEFAULT NULL,
  `session_seconds` int(11) DEFAULT 0,
  `active` tinyint(1) DEFAULT 1,
  `terminate_cause` varchar(64) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `user_transactions`
--

CREATE TABLE `user_transactions` (
  `id` int(11) NOT NULL,
  `transaction_uuid` varchar(64) DEFAULT NULL,
  `client_phone` varchar(32) DEFAULT NULL,
  `plan_id` int(11) DEFAULT NULL,
  `amount` decimal(10,2) DEFAULT NULL,
  `status` enum('pending','success','failed','processing') DEFAULT 'pending',
  `merchant_request_id` varchar(128) DEFAULT NULL,
  `checkout_request_id` varchar(128) DEFAULT NULL,
  `mpesa_receipt` varchar(64) DEFAULT NULL,
  `mac` varchar(64) DEFAULT NULL,
  `ip` varchar(64) DEFAULT NULL,
  `username` varchar(128) DEFAULT NULL,
  `sessionid` varchar(128) DEFAULT NULL,
  `callback_received_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT NULL,
  `expires_at` datetime DEFAULT NULL,
  `last_query_time` datetime DEFAULT NULL,
  `query_count` int(11) DEFAULT 0,
  `link_login` varchar(200) DEFAULT NULL,
  `code_6char` varchar(20) NOT NULL DEFAULT 'Hello@2020',
  `mikrotik_id` int(11) DEFAULT NULL,
  `vendor_id` char(36) DEFAULT NULL,
  `mikrotik_identity_name` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `user_transactions`
--

INSERT INTO `user_transactions` (`id`, `transaction_uuid`, `client_phone`, `plan_id`, `amount`, `status`, `merchant_request_id`, `checkout_request_id`, `mpesa_receipt`, `mac`, `ip`, `username`, `sessionid`, `callback_received_at`, `created_at`, `updated_at`, `expires_at`, `last_query_time`, `query_count`, `link_login`, `code_6char`, `mikrotik_id`, `vendor_id`, `mikrotik_identity_name`) VALUES
(126, '34c3ef6e-bee8-4972-863c-750a58ecbd96', '254712083124', 1, 1.00, 'success', '5859-47c2-9623-65a1da3a10bb22668', 'ws_CO_10122025093230997712083124', 'TLAAR0IQ20', 'E2:04:40:FC:F3:3C', '10.0.0.249', '254712083124', '$(sessionid)', '2025-12-10 09:32:39', '2025-12-10 09:32:27', '2025-12-10 09:32:39', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', '5cUY4B', NULL, NULL, NULL),
(127, 'b2f663a5-b845-4391-9893-be86b3143390', '254712083124', 1, 1.00, 'success', 'cf80-4b56-b361-22d8ec0e178e24489', 'ws_CO_10122025095035500712083124', 'TLAAR0IQBN', 'E2:04:40:FC:F3:3C', '10.0.0.249', '254712083124', '$(sessionid)', '2025-12-10 09:50:48', '2025-12-10 09:50:32', '2025-12-10 09:50:48', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Q1u7aV', NULL, NULL, NULL),
(128, '4189e217-957f-4d20-95da-09895cebd7dc', '254712083124', 1, 1.00, 'failed', '2780-498f-9556-ca6dc173b27f2116', 'ws_CO_10122025212000553712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-10 21:19:52', '2025-12-10 21:29:28', NULL, '2025-12-10 21:27:28', 3, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(129, '14dddc69-3d0c-4e21-a8ff-06037497405e', '254712083124', 1, 1.00, 'success', '5859-47c2-9623-65a1da3a10bb30221', 'ws_CO_10122025212100672712083124', 'TLAAR0LA96', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-10 21:21:19', '2025-12-10 21:20:49', '2025-12-10 21:21:19', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', 'PQU7rV', NULL, NULL, NULL),
(130, 'f3e4d066-aa7a-43d4-8a68-1bb347c72ae2', '254712083124', 1, 1.00, 'success', '2780-498f-9556-ca6dc173b27f2515', 'ws_CO_10122025220945295712083124', 'TLAAR0LCIF', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-10 22:10:09', '2025-12-10 22:09:38', '2025-12-10 22:10:09', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', 'J1sB02', NULL, NULL, NULL),
(131, '2186e490-eb7a-4eaa-8eb1-9078d42aeffa', '254712083124', 1, 1.00, 'success', '5859-47c2-9623-65a1da3a10bb30682', 'ws_CO_10122025221347541712083124', 'TLAAR0LFGE', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-10 22:13:57', '2025-12-10 22:13:43', '2025-12-10 22:13:57', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', '0Q6wHP', NULL, NULL, NULL),
(132, 'a0292cd4-f5c9-457d-be47-a468a54d6765', '254712083124', 1, 1.00, 'success', '5859-47c2-9623-65a1da3a10bb30789', 'ws_CO_10122025222545586712083124', 'TLAAR0LHOZ', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-10 22:25:56', '2025-12-10 22:25:39', '2025-12-10 22:25:56', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', 'Ri8rH5', NULL, NULL, NULL),
(133, '0cbd5b78-6dba-420f-a199-696259b81a78', '254712083124', 1, 1.00, 'success', '5859-47c2-9623-65a1da3a10bb30813', 'ws_CO_10122025222934557712083124', 'TLAAR0LIY3', 'E2:04:40:FC:F3:3C', '10.0.0.249', '254712083124', '$(sessionid)', '2025-12-10 22:29:47', '2025-12-10 22:29:27', '2025-12-10 22:29:47', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'sX9PW6', NULL, NULL, NULL),
(134, 'a596b9aa-2d0a-4258-9e27-91487e640993', '254712083124', 1, 1.00, 'success', 'e937-4a45-a177-69231e42ff896877', 'ws_CO_10122025223708554712083124', 'TLAAR0LKKU', 'E2:04:40:FC:F3:3C', '10.0.0.249', '254712083124', '$(sessionid)', '2025-12-10 22:37:20', '2025-12-10 22:37:00', '2025-12-10 22:37:20', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'sY6Dr1', NULL, NULL, NULL),
(135, 'ee8b9c87-0ac8-4b7c-b0d3-0cba489ad92f', '254712083124', 1, 1.00, 'success', '56e8-481d-b838-dbeabb2658c42149', 'ws_CO_10122025231229386712083124', 'TLAAR0LMCM', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-10 23:12:38', '2025-12-10 23:12:21', '2025-12-10 23:12:38', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'a4I8kn', NULL, NULL, NULL),
(136, '7ab2d9f6-318d-4da8-8578-97aaf4503232', '254712083124', 1, 1.00, 'success', '2780-498f-9556-ca6dc173b27f3125', 'ws_CO_10122025232307413712083124', 'TLAAR0LJDL', 'E2:04:40:FC:F3:3C', '10.0.0.249', '254712083124', '$(sessionid)', '2025-12-10 23:23:17', '2025-12-10 23:23:01', '2025-12-10 23:23:17', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Rj2G5G', NULL, NULL, NULL),
(137, '3c3df55a-ad54-45e3-a94b-5eb86358ec78', '254712083124', 1, 1.00, 'success', '2780-498f-9556-ca6dc173b27f3348', 'ws_CO_10122025235125079712083124', 'TLAAR0LQGD', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-10 23:51:41', '2025-12-10 23:51:19', '2025-12-10 23:51:41', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', '4qVD1T', NULL, NULL, NULL),
(138, 'a61937b6-bd26-4ae1-b59b-a1696302cee3', '254712083124', 1, 1.00, 'success', 'e937-4a45-a177-69231e42ff898546', 'ws_CO_11122025015536889712083124', 'TLBAR0LV1E', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-11 01:55:50', '2025-12-11 01:55:32', '2025-12-11 01:55:50', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'TLWL42', NULL, NULL, NULL),
(139, 'cb153701-0a18-40b3-b691-4404e0cc2d17', '254712083124', 1, 1.00, 'success', '2780-498f-9556-ca6dc173b27f4555', 'ws_CO_11122025022152859712083124', 'TLBAR0LRZI', '6C:0B:84:69:D4:73', '10.0.0.250', '', '$(sessionid)', '2025-12-11 02:22:05', '2025-12-11 02:21:48', '2025-12-11 02:22:05', NULL, NULL, 0, 'http://levine.net/login', 'b43WA6', NULL, NULL, NULL),
(140, '93b83fb0-0772-428b-98fe-26f08815b626', '254712083124', 1, 1.00, 'success', '56e8-481d-b838-dbeabb2658c410005', 'ws_CO_11122025133300278712083124', 'TLBAR0N78B', 'E2:04:40:FC:F3:3C', '10.0.0.249', '254712083124', '$(sessionid)', '2025-12-11 13:33:15', '2025-12-11 13:32:51', '2025-12-11 13:33:15', NULL, NULL, 0, 'http://levine.net/login', '32yqJG', NULL, NULL, NULL),
(141, '6696c432-3842-43a6-a088-599167d2db90', '254712083124', 1, 1.00, 'success', '2780-498f-9556-ca6dc173b27f13824', 'ws_CO_11122025185018737712083124', 'TLBAR0O6NH', 'EE:D6:76:CE:8C:D7', '10.0.0.245', '', '$(sessionid)', '2025-12-11 18:50:29', '2025-12-11 18:50:17', '2025-12-11 18:50:29', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fcaptive.apple.com%2F', 'VvZE25', NULL, NULL, NULL),
(142, 'cb3a3888-21ff-4b34-973a-7e8d5952a288', '254712083124', 1, 1.00, 'success', '56e8-481d-b838-dbeabb2658c413748', 'ws_CO_11122025204300928712083124', 'TLBAR0OTKV', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-11 20:43:19', '2025-12-11 20:42:59', '2025-12-11 20:43:19', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', 'd5ACdg', NULL, NULL, NULL),
(143, '214b8dc4-6c9f-448e-806f-564c60db577e', '254712083124', 1, 1.00, 'success', '2780-498f-9556-ca6dc173b27f15543', 'ws_CO_11122025223028076712083124', 'TLBAR0P37M', 'E2:04:40:FC:F3:3C', '10.0.0.249', '254712083124', '$(sessionid)', '2025-12-11 22:30:40', '2025-12-11 22:30:26', '2025-12-11 22:30:40', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', '318EHG', NULL, NULL, NULL),
(144, 'ca970bba-f80c-4616-a162-564e2b96ce39', '254712083124', 1, 1.00, 'success', '56e8-481d-b838-dbeabb2658c415190', 'ws_CO_11122025235330822712083124', 'TLBAR0P53O', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-11 23:53:40', '2025-12-11 23:53:27', '2025-12-11 23:53:40', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'eXNGS5', NULL, NULL, NULL),
(145, '53b9041b-37bd-4fd9-94a2-fa6202a71a5a', '254712083124', 1, 1.00, 'success', '17d4-4d72-a1b4-92738cbe0708164', 'ws_CO_12122025003114362712083124', 'TLCAR0PCWT', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-12 00:31:24', '2025-12-12 00:31:12', '2025-12-12 00:31:24', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', '37UZ5Q', NULL, NULL, NULL),
(146, '90b9685f-cf3f-437c-a36f-3ae78aad58cb', '254712083124', 1, 1.00, 'failed', 'bb14-4675-a9e7-fe3917fec920942', 'ws_CO_12122025212629960712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-12 21:26:21', '2025-12-12 21:42:10', NULL, '2025-12-12 21:35:42', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(147, '66aa8fc8-aef1-4125-93fa-38a58a58873e', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb56252', 'ws_CO_12122025213007470712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-12 21:30:02', '2025-12-12 21:46:47', NULL, '2025-12-12 21:44:40', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(148, '8841383d-4de5-4105-9e96-4eb752e7145f', '254712083124', 1, 1.00, 'failed', 'd4b7-41bb-bb8a-cc6ec5ea8bfa6698', 'ws_CO_12122025213132107712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-12 21:31:26', '2025-12-12 21:46:47', NULL, '2025-12-12 21:44:47', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(149, 'e3d7eca4-d234-4c8a-b17b-6bebd705866e', '254712083124', 1, 1.00, 'failed', 'd4b7-41bb-bb8a-cc6ec5ea8bfa7021', 'ws_CO_12122025220337711712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-12 22:03:33', '2025-12-12 22:12:31', NULL, '2025-12-12 22:10:28', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(150, '7661bf05-23fd-4d81-aec3-dcfe925221ed', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb56581', 'ws_CO_12122025220826995712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-12 22:08:24', '2025-12-12 22:18:13', NULL, '2025-12-12 22:16:02', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(151, '1aaaacfe-cc71-48f2-bcc4-e7fdc7d5a780', '254791241206', 1, 1.00, 'failed', 'bb14-4675-a9e7-fe3917fec9201342', 'ws_CO_12122025221055492791241206', NULL, '', '', '', '$(sessionid)', NULL, '2025-12-12 22:10:49', '2025-12-12 22:20:26', NULL, '2025-12-12 22:18:26', 3, '', 'Hello@2020', NULL, NULL, NULL),
(152, '441a330e-8395-4cbb-94a1-561df83cecae', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb56817', 'ws_CO_12122025223451278712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-12 22:34:46', '2025-12-12 22:44:14', NULL, '2025-12-12 22:42:01', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(153, 'ea738030-f4a7-4126-b832-f58322811eb0', '254712083124', 1, 1.00, 'failed', 'd4b7-41bb-bb8a-cc6ec5ea8bfa7329', 'ws_CO_12122025223625390712083124', NULL, '', '', '', '$(sessionid)', NULL, '2025-12-12 22:36:23', '2025-12-12 22:45:14', NULL, '2025-12-12 22:43:14', 3, '', 'Hello@2020', NULL, NULL, NULL),
(154, '1d2a2710-f590-4068-94a2-1e4e211bed60', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb58086', 'ws_CO_13122025005202510712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-13 00:51:55', '2025-12-13 01:00:45', NULL, '2025-12-13 00:58:45', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(155, '84d53244-9ec4-4a12-90a6-f9ffd3055be3', '254791241206', 1, 1.00, 'failed', '8314-4da9-b471-0322c4e1c385850', 'ws_CO_13122025192204073791241206', NULL, '', '', '', '$(sessionid)', NULL, '2025-12-13 19:22:01', '2025-12-13 19:30:08', NULL, '2025-12-13 19:28:08', 3, '', 'Hello@2020', NULL, NULL, NULL),
(156, '5c123e09-5783-457b-8462-562507b356f4', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb68152', 'ws_CO_13122025195521749712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-13 19:55:19', '2025-12-13 20:04:14', NULL, '2025-12-13 20:02:14', 3, 'http://levine.net/login', 'Hello@2020', NULL, NULL, NULL),
(157, '5a1e56a8-621c-4094-b951-bdbf566cba44', '254712083124', 1, 1.00, 'failed', 'f799-4471-95b9-213b7e8c165021944', 'ws_CO_13122025200315683712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-13 20:03:14', '2025-12-13 20:11:20', NULL, '2025-12-13 20:09:20', 3, 'http://levine.net/login', 'Hello@2020', NULL, NULL, NULL),
(158, '6d3b8f4b-af30-4e7e-97c2-54f0465e7737', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb69820', 'ws_CO_13122025233335849712083124', NULL, '', '', '', '$(sessionid)', NULL, '2025-12-13 23:33:34', '2025-12-13 23:41:58', NULL, '2025-12-13 23:39:58', 3, '', 'Hello@2020', NULL, NULL, NULL),
(159, '500702aa-1d1c-4686-bc67-ea05d16353e9', '254708374149', 1, 1.00, 'failed', 'f799-4471-95b9-213b7e8c165023809', 'ws_CO_13122025234519924708374149', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-13 23:45:18', '2025-12-13 23:54:07', NULL, '2025-12-13 23:52:04', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(160, '9c12a8ce-30ed-4dab-a007-805110fefcab', '254708374149', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb69942', 'ws_CO_13122025234909997708374149', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-13 23:49:08', '2025-12-13 23:58:15', NULL, '2025-12-13 23:56:13', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(161, 'd9969ef0-cae7-4519-9b79-c8c11e864940', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb69950', 'ws_CO_13122025235001090712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-13 23:49:59', '2025-12-13 23:58:15', NULL, '2025-12-13 23:56:15', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(162, 'c414dcc8-15e1-40b6-8d32-974f3684f3f2', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb74458', 'ws_CO_14122025092931261712083124', NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 09:29:27', '2025-12-14 09:38:04', NULL, '2025-12-14 09:36:04', 3, '', 'Hello@2020', NULL, NULL, NULL),
(163, '00cea56e-257a-419d-9ba7-f8f1c0090cb2', '254712083124', 1, 1.00, 'failed', NULL, NULL, NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 09:49:21', '2025-12-14 09:52:04', NULL, NULL, 0, '', 'Hello@2020', NULL, NULL, NULL),
(164, '879b6ff1-a57b-4a20-afff-a0127b0f9302', '254712083124', 1, 1.00, 'failed', NULL, NULL, NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 09:54:21', '2025-12-14 09:56:34', NULL, NULL, 0, '', 'Hello@2020', NULL, NULL, NULL),
(165, '362526ce-07cc-4609-a0a7-9cbe404fab7f', '254712083124', 1, 1.00, 'failed', NULL, NULL, NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 09:55:46', '2025-12-14 09:58:34', NULL, NULL, 0, '', 'Hello@2020', NULL, NULL, NULL),
(166, '0234418a-6f16-49bf-a281-af091ed7c07a', '254712083124', 1, 1.00, 'failed', NULL, NULL, NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 09:57:24', '2025-12-14 09:59:34', NULL, NULL, 0, '', 'Hello@2020', NULL, NULL, NULL),
(167, 'e9253048-8402-4bfc-983a-ecd2b504fe07', '254712083124', 1, 1.00, 'failed', NULL, NULL, NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 09:58:53', '2025-12-14 10:01:34', NULL, NULL, 0, '', 'Hello@2020', NULL, NULL, NULL),
(168, '4968d48b-665f-4c5f-9e3c-759c4f5fa146', '254791241206', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb74829', 'ws_CO_14122025101013950791241206', NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 10:10:12', '2025-12-14 10:18:41', NULL, '2025-12-14 10:16:41', 3, '', 'Hello@2020', NULL, NULL, NULL),
(169, 'd0f8af26-5531-469f-b6c4-b7e246e799b6', '254712083124', 1, 1.00, 'failed', '6b51-4f35-b5e2-96561b2833d55', 'ws_CO_14122025102533037712083124', NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 10:25:30', '2025-12-14 10:34:29', NULL, '2025-12-14 10:32:26', 3, '', 'Hello@2020', NULL, NULL, NULL),
(170, '1c71931e-5ccb-4cc9-a60c-03903ae1290c', '254791241206', 1, 1.00, 'failed', '6b51-4f35-b5e2-96561b2833d510', 'ws_CO_14122025102604686791241206', NULL, '$(mac)', '$(ip)', '$(username)', '$(sessionid)', NULL, '2025-12-14 10:26:02', '2025-12-14 10:34:29', NULL, '2025-12-14 10:32:29', 3, '$(link-login)', 'Hello@2020', NULL, NULL, NULL),
(171, '07f15375-9f76-4f24-9b0a-22a420585b9d', '254791241206', 1, 1.00, 'failed', '6b51-4f35-b5e2-96561b2833d549', 'ws_CO_14122025103215773791241206', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 10:32:13', '2025-12-14 10:40:35', NULL, '2025-12-14 10:38:35', 3, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(172, 'b6fc35de-a5e6-43dc-ba78-b71c97f650a6', '254791241206', 1, 1.00, 'failed', 'f799-4471-95b9-213b7e8c165029427', 'ws_CO_14122025111353262791241206', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 11:13:48', '2025-12-14 11:23:09', NULL, '2025-12-14 11:20:59', 3, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(173, '77788572-65f4-4e35-928c-fcb3e0968ac1', '254791241206', 1, 1.00, 'failed', 'f799-4471-95b9-213b7e8c165029432', 'ws_CO_14122025111423766791241206', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 11:14:21', '2025-12-14 11:23:09', NULL, '2025-12-14 11:21:01', 3, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(174, 'a03acde4-e7bc-4312-aee3-c8848b44fd48', '254791241206', 1, 1.00, 'failed', 'f799-4471-95b9-213b7e8c165029440', 'ws_CO_14122025111611270791241206', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 11:16:09', '2025-12-14 11:25:15', NULL, '2025-12-14 11:23:11', 3, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(175, '80b9feed-c150-46ae-af1f-45afaebb8f91', '254712083124', 1, 1.00, 'failed', 'f799-4471-95b9-213b7e8c165029441', 'ws_CO_14122025111631172712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 11:16:29', '2025-12-14 11:25:15', NULL, '2025-12-14 11:23:15', 3, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(176, 'a0cae283-0884-41d0-ba37-d9b473094fa6', '254712083124', 1, 1.00, 'failed', 'bb14-4675-a9e7-fe3917fec92020619', 'ws_CO_14122025113046701712083124', NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 11:30:44', '2025-12-14 11:39:43', NULL, '2025-12-14 11:37:42', 3, '', 'Hello@2020', NULL, NULL, NULL),
(177, '80f4fb98-be0e-4f54-82d8-919997fbff74', '254712083124', 1, 1.00, 'failed', '8314-4da9-b471-0322c4e1c3858895', 'ws_CO_14122025114006031712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 11:40:04', '2025-12-14 11:48:51', NULL, '2025-12-14 11:46:51', 3, 'http://levine.net/login?dst=http%3A%2F%2Fdevelopers.google.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(178, '23125c2f-2e9b-4e5d-82b1-99dd5d15fc30', '254791241206', 1, 1.00, 'failed', 'bb14-4675-a9e7-fe3917fec92021010', 'ws_CO_14122025121512259791241206', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 12:15:05', '2025-12-14 12:24:08', NULL, '2025-12-14 12:22:08', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(179, '6aa142f4-833b-479d-b320-defab880fa23', '254712083124', 1, 1.00, 'failed', '8314-4da9-b471-0322c4e1c3859649', 'ws_CO_14122025130331198712083124', NULL, '6C:0B:84:69:D4:73', '10.0.0.250', '254712083124', '$(sessionid)', NULL, '2025-12-14 13:03:29', '2025-12-14 13:12:14', NULL, '2025-12-14 13:10:14', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(180, '4e1dd290-c533-436c-98a6-c193f34816c1', '254712083124', 1, 1.00, 'failed', 'bb14-4675-a9e7-fe3917fec92021519', 'ws_CO_14122025131217410712083124', NULL, '6C:0B:84:69:D4:73', '10.0.0.250', '254712083124', '$(sessionid)', NULL, '2025-12-14 13:12:15', '2025-12-14 13:21:20', NULL, '2025-12-14 13:19:20', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(181, 'e453adb0-82ce-45cd-bd76-9fa4a195ab89', '254712083124', 1, 1.00, 'failed', '8314-4da9-b471-0322c4e1c38510140', 'ws_CO_14122025135334558712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 13:53:33', '2025-12-14 14:02:25', NULL, '2025-12-14 14:00:25', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(182, '2e00e337-d1dc-4e45-bbf6-9af950d5c577', '254791241206', 1, 1.00, 'failed', 'bb14-4675-a9e7-fe3917fec92022089', 'ws_CO_14122025142142531791241206', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 14:21:41', '2025-12-14 14:30:31', NULL, '2025-12-14 14:28:31', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(183, 'e256174e-5a19-4ede-a23a-a5c9a6cd310e', '254712083124', 1, 1.00, 'failed', 'bb14-4675-a9e7-fe3917fec92022194', 'ws_CO_14122025143252613712083124', NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 14:32:50', '2025-12-14 14:41:39', NULL, '2025-12-14 14:39:38', 3, '', 'Hello@2020', NULL, NULL, NULL),
(184, 'b7ec572e-6726-46ea-9cee-0bd939e4f623', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb77138', 'ws_CO_14122025144508179712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 14:45:06', '2025-12-14 14:53:47', NULL, '2025-12-14 14:51:47', 3, 'http://levine.net/login', 'Hello@2020', NULL, NULL, NULL),
(185, '70b57893-9076-46c9-9b85-e2f51027d164', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb77288', 'ws_CO_14122025150337180712083124', NULL, '6C:0B:84:69:D4:73', '10.0.0.250', '', '$(sessionid)', NULL, '2025-12-14 15:03:35', '2025-12-14 15:11:55', NULL, '2025-12-14 15:09:55', 3, 'http://levine.net/login', 'Hello@2020', NULL, NULL, NULL),
(186, 'e3a16a62-84ed-4df9-8f5b-f8c711188dbc', '254712083124', 1, 1.00, 'failed', 'bb14-4675-a9e7-fe3917fec92022562', 'ws_CO_14122025151939987712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 15:19:37', '2025-12-14 15:28:58', NULL, '2025-12-14 15:26:08', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(187, '5e1387eb-4999-4a2f-bd97-c9edcd36df62', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb77761', 'ws_CO_14122025160125215712083124', NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 16:01:23', '2025-12-14 16:10:06', NULL, '2025-12-14 16:08:06', 3, '', 'Hello@2020', NULL, NULL, NULL),
(188, '1cc9a142-2169-418c-aabd-497946a962ae', '254712083124', 1, 1.00, 'failed', NULL, NULL, NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 17:28:12', '2025-12-14 17:31:07', NULL, NULL, 0, '', 'Hello@2020', NULL, NULL, NULL),
(189, 'c026daaf-4258-4959-89c9-6be68f0b1df6', '254712083124', 1, 1.00, 'failed', NULL, NULL, NULL, '', '', '', '$(sessionid)', NULL, '2025-12-14 17:50:58', '2025-12-14 17:53:07', NULL, NULL, 0, '', 'Hello@2020', NULL, NULL, NULL),
(190, 'e112962d-e219-4023-b0a6-c613e0357cfc', '254712083124', 1, 1.00, 'failed', 'bb14-4675-a9e7-fe3917fec92023974', 'ws_CO_14122025190939454712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-14 19:09:38', '2025-12-14 19:18:18', NULL, '2025-12-14 19:16:18', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(191, '803df93b-eb32-48b7-8886-dd4a150ce050', '254712083124', 1, 1.00, 'failed', '5859-47c2-9623-65a1da3a10bb79835', 'ws_CO_14122025212439175712083124', NULL, '6C:0B:84:69:D4:73', '10.0.0.250', '', '$(sessionid)', NULL, '2025-12-14 21:24:34', '2025-12-14 21:33:30', NULL, '2025-12-14 21:31:30', 3, 'http://levine.net/login', 'Hello@2020', NULL, NULL, NULL),
(192, 'f291f1f2-e996-4514-863b-f7ecfdbd0984', '254712083124', 1, 1.00, 'failed', 'bb14-4675-a9e7-fe3917fec92025948', 'ws_CO_14122025220206917712083124', NULL, '6C:0B:84:69:D4:73', '10.0.0.250', '', '$(sessionid)', NULL, '2025-12-14 22:01:59', '2025-12-14 22:31:52', NULL, '2025-12-14 22:29:52', 3, 'http://levine.net/login', 'Hello@2020', NULL, NULL, NULL),
(193, '2fa8ec72-f680-4f0f-be10-d4bd6993e5a4', '254712083124', 1, 1.00, 'failed', '8314-4da9-b471-0322c4e1c38517531', 'ws_CO_15122025000425703712083124', NULL, '', '', '', '$(sessionid)', NULL, '2025-12-15 00:04:24', '2025-12-15 00:12:59', NULL, '2025-12-15 00:10:59', 3, '', 'Hello@2020', NULL, NULL, NULL),
(194, 'bc4dbe55-14af-4ea7-920a-c6e5c091e394', '254712083124', 1, 1.00, 'failed', 'bb14-4675-a9e7-fe3917fec92029502', 'ws_CO_15122025010150642712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-15 01:01:46', '2025-12-15 01:10:09', NULL, '2025-12-15 01:08:09', 3, 'http://levine.net/login', 'Hello@2020', NULL, NULL, NULL),
(195, 'e9d0e586-27a3-4fc5-8798-bdfc6b553a31', '254713649664', 1, 1.00, 'failed', '8314-4da9-b471-0322c4e1c38527632', 'ws_CO_15122025213928808713649664', NULL, 'EA:1D:A2:0A:B1:1F', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-15 21:39:27', '2025-12-15 21:39:43', NULL, NULL, 0, 'http://levine.net/login', 'Hello@2020', NULL, NULL, NULL),
(196, 'cace48bf-af32-4dab-a556-8b8c727d99c7', '254791241206', 1, 1.00, 'failed', '2a9f-44c2-9e2e-eb20ca0504699979', 'ws_CO_15122025215835572791241206', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-15 21:58:33', '2025-12-15 22:01:04', NULL, '2025-12-15 22:01:04', 1, 'http://levine.net/login?dst=http%3A%2F%2Fconnectivitycheck.gstatic.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(197, '4e029e0e-6003-45e6-b10c-fcb7079f635c', '254712083124', 1, 1.00, 'failed', '2a9f-44c2-9e2e-eb20ca0504699983', 'ws_CO_15122025215920503712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-15 21:59:18', '2025-12-15 21:59:28', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fconnectivitycheck.gstatic.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(198, 'a56c432f-1f73-484e-8f32-ba66501727c6', '254791241206', 1, 1.00, 'success', '6538-4a51-9ae9-fea03ad44e6110862', 'ws_CO_15122025222512431791241206', 'TLFEK13U9F', 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', '2025-12-15 22:25:30', '2025-12-15 22:25:10', '2025-12-15 22:25:30', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fconnectivitycheck.gstatic.com%2Fgenerate%5F204', 'O5zgzR', NULL, NULL, NULL),
(199, 'c137b212-e835-4962-990c-4f8f60c17acb', '254712083124', 1, 1.00, 'failed', '0b3d-43a6-b62a-9bb068e24897264', 'ws_CO_15122025225824565712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', NULL, '2025-12-15 22:58:22', '2025-12-15 22:58:34', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', NULL, NULL, NULL),
(200, 'db3a4528-566b-40ac-a4f3-ab4e44d432f7', '254791241206', 1, 1.00, 'success', '0b3d-43a6-b62a-9bb068e24897265', 'ws_CO_15122025225913096791241206', 'TLFEK141MS', 'E2:04:40:FC:F3:3C', '10.0.0.254', '', '$(sessionid)', '2025-12-15 22:59:24', '2025-12-15 22:59:11', '2025-12-15 22:59:24', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'WW8EX5', NULL, NULL, NULL),
(201, '4ef07c50-4582-4a67-b4c7-c1072f89c35d', '254712083124', 1, 1.00, 'failed', '226e-4fd5-ba67-9c55c2a4cc182954', 'ws_CO_19122025131848847712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-19 13:18:42', '2025-12-19 13:18:56', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', 1, 'xcvt', NULL),
(202, '25f432a6-9003-4092-8456-5d5623e4120b', '254791241206', 1, 1.00, 'success', '7ce7-427b-b70b-d8b5573fa2418068', 'ws_CO_19122025194728323791241206', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-19 19:53:45', '2025-12-19 19:47:23', '2025-12-19 19:53:45', NULL, '2025-12-19 19:53:45', 3, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'aD2W89', 1, 'xcvt', 'MikroTik'),
(203, '2030830a-72ee-4ee7-84dd-10721836c753', '254791241206', 1, 1.00, 'failed', '226e-4fd5-ba67-9c55c2a4cc186432', 'ws_CO_19122025195354616791241206', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-19 19:53:50', '2025-12-19 19:54:17', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', 1, 'xcvt', 'MikroTik'),
(204, 'b8e53281-c093-4b3f-9972-da9eb27cafaf', '254791241206', 1, 1.00, 'success', '14b6-4618-9f19-df58f46b1a4b6926', 'ws_CO_19122025195553891791241206', 'TLJEK1GISJ', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-19 19:56:11', '2025-12-19 19:55:49', '2025-12-19 19:56:11', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'B2RFR9', 1, 'xcvt', 'MikroTik'),
(205, 'd468d91f-6f0d-4d8c-91d3-843a2a3b57b2', '254748308923', 1, 1.00, 'success', '14b6-4618-9f19-df58f46b1a4b7673', 'ws_CO_19122025212106803748308923', 'TLJ0F1C5YU', '82:F7:38:13:4F:88', '10.0.0.248', '', '$(sessionid)', '2025-12-19 21:21:17', '2025-12-19 21:21:00', '2025-12-19 21:21:17', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fconnectivitycheck.gstatic.com%2Fgenerate%5F204', 'W4jNGf', 1, 'xcvt', 'MikroTik'),
(206, '270c3683-258d-4c95-ad83-c543e82d6a55', '254791241206', 1, 1.00, 'failed', 'cc67-4f91-8b89-10b40a86e2a3327', 'ws_CO_19122025212111814791241206', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-19 21:21:06', '2025-12-19 21:21:38', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'Hello@2020', 1, 'xcvt', 'MikroTik'),
(207, '4b6274fb-15cf-4d7f-81c7-2860fb522496', '254791241206', 1, 1.00, 'success', '226e-4fd5-ba67-9c55c2a4cc187236', 'ws_CO_19122025212356222791241206', 'TLJEK1GOGO', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-19 21:24:19', '2025-12-19 21:23:51', '2025-12-19 21:24:19', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', '9cZTyR', 1, 'xcvt', 'MikroTik'),
(208, '90bcac29-1f75-4aa2-92a6-7ad2d65eaf16', '254791241206', 1, 1.00, 'success', 'cc67-4f91-8b89-10b40a86e2a31437', 'ws_CO_19122025233338397791241206', 'TLJEK1GZ3L', 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', '2025-12-19 23:33:51', '2025-12-19 23:33:36', '2025-12-19 23:33:51', NULL, NULL, 0, 'http://levine.net/login?dst=http%3A%2F%2Fwww.googleapis.com%2Fgenerate%5F204', 'ueWM3Z', 1, 'xcvt', 'MikroTik'),
(209, '1b586674-81f1-4a25-aab4-152ba2dc75eb', '254712083124', 1, 1.00, 'failed', '7ce7-427b-b70b-d8b5573fa24110554', 'ws_CO_20122025005126202712083124', NULL, 'E2:04:40:FC:F3:3C', '10.0.0.249', '', '$(sessionid)', NULL, '2025-12-20 00:51:25', '2025-12-20 00:51:41', NULL, NULL, 0, 'http://levine.net/login', 'Hello@2020', 1, 'xcvt', 'MikroTik');

-- --------------------------------------------------------

--
-- Table structure for table `vendors`
--

CREATE TABLE `vendors` (
  `id` char(36) NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `status` enum('ACTIVE','SUSPENDED') DEFAULT 'ACTIVE',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `vendors`
--

INSERT INTO `vendors` (`id`, `name`, `status`, `created_at`) VALUES
('xcvt', 'JOHN DOE', 'ACTIVE', '2025-12-17 19:37:31');

-- --------------------------------------------------------

--
-- Table structure for table `vendor_mpesa_configs`
--

CREATE TABLE `vendor_mpesa_configs` (
  `vendor_id` char(36) NOT NULL,
  `business_shortcode` varchar(20) DEFAULT NULL,
  `passkey` varchar(255) DEFAULT NULL,
  `consumer_key` varchar(255) DEFAULT NULL,
  `consumer_secret` varchar(255) DEFAULT NULL,
  `callback_url` varchar(255) DEFAULT NULL,
  `environment` enum('SANDBOX','PRODUCTION') DEFAULT NULL,
  `enabled` tinyint(4) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `vendor_mpesa_configs`
--

INSERT INTO `vendor_mpesa_configs` (`vendor_id`, `business_shortcode`, `passkey`, `consumer_key`, `consumer_secret`, `callback_url`, `environment`, `enabled`) VALUES
('xcvt', '174379', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919', 'GkAVcpDI955MZqyqAwj8IDec5hrGeqoAXGWDNCKSw1DLgXJb', 'sqD24UHTDO58AoGwJ6Ep3tA06Rs8cUKvwR5BsHMM0mGRXTJJZGKmBm9X2iZI0eHt', 'https://unrollable-cecelia-unshrined.ngrok-free.dev/callback', 'SANDBOX', 1);

-- --------------------------------------------------------

--
-- Table structure for table `vendor_wallets`
--

CREATE TABLE `vendor_wallets` (
  `vendor_id` char(36) NOT NULL,
  `balance` decimal(10,2) DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `hotspot_users`
--
ALTER TABLE `hotspot_users`
  ADD PRIMARY KEY (`id`),
  ADD KEY `mikrotik_id` (`mikrotik_id`),
  ADD KEY `fk_hotspot_users_plan` (`plan_id`),
  ADD KEY `fk_hotspot_users_vendor` (`vendor_id`);

--
-- Indexes for table `mikrotik_devices`
--
ALTER TABLE `mikrotik_devices`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `serial_number` (`serial_number`),
  ADD KEY `vendor_id` (`vendor_id`);

--
-- Indexes for table `plans`
--
ALTER TABLE `plans`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `radius_sessions`
--
ALTER TABLE `radius_sessions`
  ADD PRIMARY KEY (`acct_session_id`),
  ADD KEY `mikrotik_id` (`mikrotik_id`);

--
-- Indexes for table `router_revenue_rules`
--
ALTER TABLE `router_revenue_rules`
  ADD PRIMARY KEY (`mikrotik_id`);

--
-- Indexes for table `transactions`
--
ALTER TABLE `transactions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `transaction_uuid` (`transaction_uuid`);

--
-- Indexes for table `user_plans`
--
ALTER TABLE `user_plans`
  ADD PRIMARY KEY (`id`),
  ADD KEY `mikrotik_id` (`mikrotik_id`);

--
-- Indexes for table `user_sessions`
--
ALTER TABLE `user_sessions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_radacct` (`radacctid`),
  ADD KEY `idx_active` (`active`),
  ADD KEY `idx_vendor` (`vendor_id`),
  ADD KEY `idx_router` (`mikrotik_id`);

--
-- Indexes for table `user_transactions`
--
ALTER TABLE `user_transactions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `transaction_uuid` (`transaction_uuid`),
  ADD KEY `mikrotik_id` (`mikrotik_id`),
  ADD KEY `vendor_id` (`vendor_id`);

--
-- Indexes for table `vendors`
--
ALTER TABLE `vendors`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `vendor_mpesa_configs`
--
ALTER TABLE `vendor_mpesa_configs`
  ADD PRIMARY KEY (`vendor_id`);

--
-- Indexes for table `vendor_wallets`
--
ALTER TABLE `vendor_wallets`
  ADD PRIMARY KEY (`vendor_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `hotspot_users`
--
ALTER TABLE `hotspot_users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=59;

--
-- AUTO_INCREMENT for table `mikrotik_devices`
--
ALTER TABLE `mikrotik_devices`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `plans`
--
ALTER TABLE `plans`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `transactions`
--
ALTER TABLE `transactions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=83;

--
-- AUTO_INCREMENT for table `user_plans`
--
ALTER TABLE `user_plans`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `user_sessions`
--
ALTER TABLE `user_sessions`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `user_transactions`
--
ALTER TABLE `user_transactions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=210;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `hotspot_users`
--
ALTER TABLE `hotspot_users`
  ADD CONSTRAINT `fk_hotspot_users_plan` FOREIGN KEY (`plan_id`) REFERENCES `user_plans` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_hotspot_users_vendor` FOREIGN KEY (`vendor_id`) REFERENCES `vendors` (`id`) ON UPDATE CASCADE,
  ADD CONSTRAINT `hotspot_users_ibfk_1` FOREIGN KEY (`mikrotik_id`) REFERENCES `mikrotik_devices` (`id`);

--
-- Constraints for table `mikrotik_devices`
--
ALTER TABLE `mikrotik_devices`
  ADD CONSTRAINT `mikrotik_devices_ibfk_1` FOREIGN KEY (`vendor_id`) REFERENCES `vendors` (`id`);

--
-- Constraints for table `radius_sessions`
--
ALTER TABLE `radius_sessions`
  ADD CONSTRAINT `radius_sessions_ibfk_1` FOREIGN KEY (`mikrotik_id`) REFERENCES `mikrotik_devices` (`id`);

--
-- Constraints for table `router_revenue_rules`
--
ALTER TABLE `router_revenue_rules`
  ADD CONSTRAINT `router_revenue_rules_ibfk_1` FOREIGN KEY (`mikrotik_id`) REFERENCES `mikrotik_devices` (`id`);

--
-- Constraints for table `user_plans`
--
ALTER TABLE `user_plans`
  ADD CONSTRAINT `user_plans_ibfk_1` FOREIGN KEY (`mikrotik_id`) REFERENCES `mikrotik_devices` (`id`);

--
-- Constraints for table `user_transactions`
--
ALTER TABLE `user_transactions`
  ADD CONSTRAINT `user_transactions_ibfk_1` FOREIGN KEY (`mikrotik_id`) REFERENCES `mikrotik_devices` (`id`),
  ADD CONSTRAINT `user_transactions_ibfk_2` FOREIGN KEY (`vendor_id`) REFERENCES `vendors` (`id`);

--
-- Constraints for table `vendor_mpesa_configs`
--
ALTER TABLE `vendor_mpesa_configs`
  ADD CONSTRAINT `vendor_mpesa_configs_ibfk_1` FOREIGN KEY (`vendor_id`) REFERENCES `vendors` (`id`);

--
-- Constraints for table `vendor_wallets`
--
ALTER TABLE `vendor_wallets`
  ADD CONSTRAINT `vendor_wallets_ibfk_1` FOREIGN KEY (`vendor_id`) REFERENCES `vendors` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
