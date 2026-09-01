<?php
require_once 'UdmurtDictionaryParser.php';

// Создаём экземпляр парсера
$parser = new UdmurtDictionaryParser();

// Парсим все страницы (с паузой 1 секунда между запросами)
$all_terms = $parser->parseAllPages(1);

// Сохраняем в CSV
$parser->saveToCsv($all_terms, 'udmurt_dictionary_full.csv');

// Сохраняем в JSON
$parser->saveToJson($all_terms, 'udmurt_dictionary_full.json');

echo "Готово! Проверьте файлы udmurt_dictionary_full.csv и udmurt_dictionary_full.json\n";
?>
