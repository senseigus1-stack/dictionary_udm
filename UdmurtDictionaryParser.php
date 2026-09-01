<?php

class UdmurtDictionaryParser {
    private $base_url;
    private $total_pages;

    public function __construct($base_url = 'https://dict.fu-lab.ru') {
        $this->base_url = $base_url;
        $this->total_pages = 0;
    }

    /**
     * Получает HTML-код страницы
     */
    private function getPageHtml($url) {
        $ch = curl_init();
        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            CURLOPT_TIMEOUT => 30,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_SSL_VERIFYPEER => false
        ]);

        $html = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($http_code !== 200) {
            throw new Exception("Ошибка загрузки страницы: HTTP {$http_code}");
        }

        return $html;
    }

    /**
     * Определяет общее количество страниц
     */
    private function detectTotalPages() {
        $first_page_url = "{$this->base_url}/dict-p?id=129449&page=1";
        $html = $this->getPageHtml($first_page_url);

        $dom = new DOMDocument();
        @$dom->loadHTML(mb_convert_encoding($html, 'HTML-ENTITIES', 'UTF-8'));
        $xpath = new DOMXPath($dom);

        $elements = $xpath->query("//div[contains(@class, 'paginator_dict_div_header_3')]");
        if ($elements->length > 0) {
            $text = $elements->item(0)->textContent;
            preg_match('/страница\s+\d+\s+из\s+(\d+)/u', $text, $matches);
            if (isset($matches[1])) {
                $this->total_pages = (int)$matches[1];
                return;
            }
        }
        $this->total_pages = 1;
    }

    /**
     * Парсит одну страницу словаря
     */
    private function parseSinglePage($page_number) {
        $url = "{$this->base_url}/dict-p?id=129449&page={$page_number}";
        echo "Парсинг страницы {$page_number} из {$this->total_pages}...\n";

        try {
            $html = $this->getPageHtml($url);
            $dom = new DOMDocument();
            @$dom->loadHTML(mb_convert_encoding($html, 'HTML-ENTITIES', 'UTF-8'));
            $xpath = new DOMXPath($dom);

            $entries = [];
            $items = $xpath->query("//div[contains(@class, 'dict_p_content_item')]");

            foreach ($items as $item) {
                // Номер записи
                $numberElement = $xpath->query(".//span[contains(@class, 'dict_p_i')]", $item);
                $number = $numberElement->length > 0 ? (int)trim($numberElement->item(0)->textContent) : null;

                // Слово и ссылка
                $linkElement = $xpath->query(".//a", $item);
                $word = $linkElement->length > 0 ? trim($linkElement->item(0)->textContent) : '';
                $detailUrl = $linkElement->length > 0 ? $linkElement->item(0)->getAttribute('href') : '';

                // Толкование
                $textElement = $xpath->query(".//span[contains(@class, 'dict_p_text')]", $item);
                $definition = $textElement->length > 0 ? trim($textElement->item(0)->textContent) : '';

                if ($word) {
                    $entries[] = [
                        'number' => $number,
                        'word' => $word,
                        'detail_url' => $detailUrl,
                        'definition' => $definition
                    ];
                }
            }

            return $entries;
        } catch (Exception $e) {
            echo "Ошибка при парсинге страницы {$page_number}: {$e->getMessage()}\n";
            return [];
        }
    }
 
    /**
     * Основной метод для парсинга всех страниц
     */
    public function parseAllPages($delay = 1) {
        // Определяем общее количество страниц
        $this->detectTotalPages();
        echo "Обнаружено страниц: {$this->total_pages}\n";

        $all_entries = [];
        $processed_pages = 0;

        for ($page = 1; $page <= $this->total_pages; $page++) {
            try {
                $entries = $this->parseSinglePage($page);
                if (!empty($entries)) {
                    $all_entries = array_merge($all_entries, $entries);
                    $processed_pages++;
                }

                // Пауза между запросами для снижения нагрузки на сервер
                if ($page < $this->total_pages) {
                    sleep($delay);
                }
            } catch (Exception $e) {
                echo "Пропущена страница {$page}: {$e->getMessage()}\n";
                continue;
            }
        }

        echo "\nПарсинг завершён! Обработано страниц: {$processed_pages}, извлечено терминов: " . count($all_entries) . "\n";
        return $all_entries;
    }

    /**
     * Сохраняет результаты в CSV-файл
     */
    public function saveToCsv($data, $filename = 'udmurt_dictionary.csv') {
        $file = fopen($filename, 'w');
        fputcsv($file, ['number', 'word', 'detail_url', 'definition'], ';', '"');

        foreach ($data as $row) {
            fputcsv($file, $row, ';', '"');
        }

        fclose($file);
        echo "Данные сохранены в файл: {$filename}\n";
    }

    /**
     * Сохраняет результаты в JSON-файл
     */
    public function saveToJson($data, $filename = 'udmurt_dictionary.json') {
        file_put_contents($filename, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        echo "Данные сохранены в файл: {$filename}\n";
    }
}
?>