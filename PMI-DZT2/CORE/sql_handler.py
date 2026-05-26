import sqlite3
from typing import List, Optional


class SQL_handler:
    def __init__(self, db_path='CORE/FunctionalBlocks.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self):    
        """Подключение к базе данных"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        return self.cursor

    def _get_base_query(self) -> str:
        """Базовый SQL-запрос для всех методов (с FunctionalBlockDescriptions)"""
        return '''
            SELECT 
                -- FblFunctionalBlocks
                fb.Name as BlockName,
                fb.Id as BlockId,
                
                -- FunctionalBlockDescriptions
                fbd.Id as BlockDescriptionId,
                fbd.TypeId,
                fbd.RussianName as BlockRussianName,
                fbd.WeightCoefficient,
                fbd.Iec61850Name as BlockIec61850Name,
                fbd.FbVersion,
                fbd.FunctionalBlockCategory,
                
                -- FblVariables
                v.Id as VariableId,
                v.Comment,
                v.Name,
                v.FullName,
                v.GebModifier,
                v.Modifier,
                v.GebType,
                v.NativeType,
                v.FblLegIndex,
                v.FblFunctionalBlockId,
                v.FblLegId,
                
                -- FblVariableDescriptions
                vd.Id as DescriptionId,
                vd.NodeNameRu,
                vd.ExcelRowIndex,
                vd.Description,
                vd.Fun_103,
                vd.Inf_103,
                vd.Inf_InstShift_103,
                vd.MappingMask,
                vd.Note,
                vd.Units,
                vd.ReadOnly,
                vd.Command,
                vd.OperativeEventRegistration,
                vd.EventRegistration,
                vd."Group",
                vd.Min,
                vd.Max,
                vd.Step,
                vd.Multiplier,
                vd.DefaultValue,
                vd.FullDescription,
                vd.AppliedDescription,
                vd.WordAddress,
                vd.BitAddress,
                vd.ValueScaleCoefficient,
                vd.SerialNumber,
                vd.ExtensionEnum,
                vd.ExtensionEnumHmi,
                vd.AuthLevel,
                vd.ConvertingFlag,
                vd.ConvertingBasis,
                vd.COM_WRITE,
                vd.Iec61850TypeLN,
                vd.Iec61850DataObjectName,
                vd.Iec61850CommonDataClass,
                vd.Iec61850AttributeName,
                vd.Iec61850AttributeType,
                vd.Iec61850EnumDAType,
                vd.Iec61850FC,
                vd.Iec61850Reference,
                vd.Iec61850PresCond,
                vd.FblVariableId
                
            FROM FblVariables v
            JOIN FblFunctionalBlocks fb ON v.FblFunctionalBlockId = fb.Id 
            LEFT JOIN FunctionalBlockDescriptions fbd ON fb.Id = fbd.FunctionalBlockId
            LEFT JOIN FblVariableDescriptions vd ON v.Id = vd.FblVariableId
            WHERE fb.Name = ?
        '''

    def get_all_data_by_fb_iecname(self, fb_iecname):
        """Получение всей информации по функциональному блоку"""
        query = self._get_base_query()
        query += ' ORDER BY v.FblLegId, v.FblLegIndex'
        
        self.cursor.execute(query, (fb_iecname,))
        return self.cursor.fetchall()

    def get_all_settings(self, fb_iecname: str) -> List[sqlite3.Row]:
        """Получить все Settings переменные"""
        query = self._get_base_query()
        query += ' AND INSTR(v.Modifier, ?) > 0'
        query += ' ORDER BY v.FblLegId, v.FblLegIndex'
        
        self.cursor.execute(query, (fb_iecname, 'Setting'))
        return self.cursor.fetchall()

    def get_all_controls(self, fb_iecname: str) -> List[sqlite3.Row]:
        """Получить все Input переменные"""
        query = self._get_base_query()
        query += ' AND v.GebModifier = ?'
        query += ' ORDER BY v.FblLegId, v.FblLegIndex'
        
        self.cursor.execute(query, (fb_iecname, 'INPUT'))
        return self.cursor.fetchall()

    def get_all_statuses(self, fb_iecname: str) -> List[sqlite3.Row]:
        """Получить все Status переменные"""
        query = self._get_base_query()
        query += ' AND v.GebModifier = ? AND v.Modifier = ?'
        query += ' ORDER BY v.FblLegId, v.FblLegIndex'
        
        self.cursor.execute(query, (fb_iecname, 'OUTPUT', 'Output'))
        return self.cursor.fetchall()

    # ──────────────────────────────────────────────────────────────
    # НОВЫЕ МЕТОДЫ ДЛЯ FunctionalBlockDescriptions
    # ──────────────────────────────────────────────────────────────

    def get_block_description(self, fb_iecname: str) -> Optional[sqlite3.Row]:
        """
        Получить описание функционального блока
        Возвращает одну строку с информацией о блоке
        """
        query = '''
            SELECT 
                fb.Name as BlockName,
                fb.Id as BlockId,
                fbd.Id as DescriptionId,
                fbd.TypeId,
                fbd.RussianName,
                fbd.WeightCoefficient,
                fbd.Iec61850Name,
                fbd.FbVersion,
                fbd.FunctionalBlockCategory
            FROM FblFunctionalBlocks fb
            LEFT JOIN FunctionalBlockDescriptions fbd ON fb.Id = fbd.FunctionalBlockId
            WHERE fb.Name = ?
        '''
        
        self.cursor.execute(query, (fb_iecname,))
        return self.cursor.fetchone()

    def get_all_block_descriptions(self) -> List[sqlite3.Row]:
        """
        Получить описания всех функциональных блоков
        """
        query = '''
            SELECT 
                fb.Name as BlockName,
                fb.Id as BlockId,
                fbd.Id as DescriptionId,
                fbd.TypeId,
                fbd.RussianName,
                fbd.WeightCoefficient,
                fbd.Iec61850Name,
                fbd.FbVersion,
                fbd.FunctionalBlockCategory
            FROM FblFunctionalBlocks fb
            LEFT JOIN FunctionalBlockDescriptions fbd ON fb.Id = fbd.FunctionalBlockId
            ORDER BY fb.Name
        '''
        
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_blocks_by_category(self, category: str) -> List[sqlite3.Row]:
        """
        Получить блоки по категории
        """
        query = '''
            SELECT 
                fb.Name as BlockName,
                fb.Id as BlockId,
                fbd.RussianName,
                fbd.Iec61850Name,
                fbd.FbVersion,
                fbd.FunctionalBlockCategory
            FROM FblFunctionalBlocks fb
            JOIN FunctionalBlockDescriptions fbd ON fb.Id = fbd.FunctionalBlockId
            WHERE fbd.FunctionalBlockCategory = ?
            ORDER BY fb.Name
        '''
        
        self.cursor.execute(query, (category,))
        return self.cursor.fetchall()

    def get_all_categories(self) -> List[str]:
        """
        Получить все уникальные категории функциональных блоков
        """
        query = '''
            SELECT DISTINCT FunctionalBlockCategory
            FROM FunctionalBlockDescriptions
            WHERE FunctionalBlockCategory IS NOT NULL
            ORDER BY FunctionalBlockCategory
        '''
        
        self.cursor.execute(query)
        return [row[0] for row in self.cursor.fetchall()]

    def disconnect(self):  
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()
            print("Соединение закрыто")