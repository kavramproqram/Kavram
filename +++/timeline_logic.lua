--[[
# Kavram 1.0.0
# Copyright (C) 2025-09-01 Kavram or Contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see /Kavram/License/GPLv3.txt
#
# ---------------------------------------------
#
# Kavram 1.0.0
# Copyright (C) 2025-09-01 Kavram veya Contributors
#
# Bu program özgür bir yazılımdır: Özgür Yazılım Vakfı tarafından yayınlanan
# GNU Genel Kamu Lisansı'nın 3. sürümü veya (tercihinize bağlı olarak)
# daha sonraki herhangi bir sürümü kapsamında yeniden dağıtabilir ve/veya
# değiştirebilirsiniz.
#
# Bu program, faydalı olacağı umuduyla dağıtılmaktadır, ancak HERHANGİ BİR
# GARANTİ OLMADAN; hatta SATILABİLİRLİK veya BELİRLİ BİR AMACA UYGUNLUK
# zımni garantisi olmaksızın.
#
# Bu programla birlikte GNU Genel Kamu Lisansı'nın bir kopyasını almış olmanız gerekir:
# /Kavram/License/GPLv3.txt
--]]



-- timeline_logic.lua
-- Zaman çizelgesi segmentlerinin konumlarını hesaplayan ve akıcılık için yardımcı olabilecek Lua fonksiyonları.

-- calculate_segment_position:
-- Belirtilen başlangıç süresi (ms), toplam zaman çizelgesi genişliği (piksel) ve
-- zaman çizelgesinin toplam süresi (ms) verildiğinde bir segmentin x pozisyonunu hesaplar.
function calculate_segment_position(start_time_ms, timeline_width, total_timeline_duration_ms)
if total_timeline_duration_ms == 0 then
    return 0 -- Bölme hatasını önlemek için
    end
    -- Oranı kullanarak piksel pozisyonunu hesapla
    local position_ratio = start_time_ms / total_timeline_duration_ms
    local x_position = position_ratio * timeline_width
    return x_position
    end

    -- update_timeline_smoothly:
    -- Bir değeri hedef değere doğru yumuşakça güncelleyen basit bir enterpolasyon fonksiyonu.
    -- Bu, UI elemanlarının daha akıcı hareket etmesi için kullanılabilir,
-- örneğin kaydırma konumunu veya segmentlerin küçük hareketlerini.
function update_timeline_smoothly(current_value, target_value, step_size)
if current_value == target_value then
    return current_value
    end

    if math.abs(target_value - current_value) < step_size then
        return target_value -- Hedefe çok yakınsa doğrudan hedefe git
        end

        if current_value < target_value then
            current_value = current_value + step_size
            else
                current_value = current_value - step_size
                end
                return current_value
                end

                -- Burada başka zaman çizelgesiyle ilgili karmaşık matematiksel veya görsel fonksiyonlar da tanımlanabilir.

